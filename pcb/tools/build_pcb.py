"""First-pass (unrouted) placement of racebot_main.kicad_pcb from the exported netlist."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
from sexp import parse, find

PCB_DIR = sys.argv[1]
FPLIB = r"C:\Program Files\KiCad\10.0\share\kicad\footprints"
OX, OY = 100.0, 100.0          # board top-left in pcbnew coordinates
mm = pcbnew.FromMM


def P(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


# ---------------------------------------------------------------- placement table (board coords, mm, deg)
W, H = 108.0, 76.0
HOLE_INSET = 3.5
PL = {
    # ESP32 DevKit headers, rows 25.4 mm apart; pin 1 near the front edge so the antenna overhangs it
    'J201': (41.3, 2.0, 0), 'J202': (66.7, 2.0, 0),
    # under the DevKit (8.5 mm socket clearance): IS filters, VBAT divider, logic buffer, pull-downs
    'R405': (46.0, 4.0, 0), 'C401': (49.5, 4.0, 0), 'D401': (53.5, 4.5, 0),
    'R410': (46.0, 9.0, 0), 'C404': (49.5, 9.0, 0), 'D402': (53.5, 9.5, 0),
    'R505': (46.0, 14.0, 0), 'C501': (49.5, 14.0, 0), 'D501': (53.5, 14.5, 0),
    'R510': (46.0, 19.0, 0), 'C504': (49.5, 19.0, 0), 'D502': (53.5, 19.5, 0),
    'R103': (60.0, 6.0, 0), 'R104': (60.0, 9.0, 0), 'C105': (60.0, 12.0, 0),
    'U301': (54.0, 32.0, 0), 'C301': (62.5, 30.0, 90),
    'R301': (46.0, 42.0, 90), 'R302': (49.0, 42.0, 90), 'R303': (52.0, 42.0, 90),
    'R304': (56.0, 42.0, 90), 'R305': (59.0, 42.0, 90), 'R306': (62.0, 42.0, 90),
    # behind the DevKit: ELRS header (clear of the DevKit USB plug) + LEDs
    'J203': (66.0, 51.6, 0),
    'R201': (44.0, 55.0, 0), 'D201': (44.0, 58.0, 0),
    'R105': (49.0, 55.0, 0), 'D104': (49.0, 58.0, 0),
    'R106': (54.0, 55.0, 0), 'D105': (54.0, 58.0, 0),
    # power entry along the rear edge: Q101 | battery XT60 (- +) | fuse | switch XT60 (VBAT_F VMOT)
    'Q101': (11.0, 69.0, 0), 'R101': (6.0, 61.5, 0), 'R102': (10.0, 61.5, 0), 'D101': (8.0, 65.0, 0),
    'J101': (20.0, 70.0, 0), 'F101': (25.0, 60.0, 0), 'J102': (46.0, 70.0, 180),
    'D102': (55.5, 64.0, 0),
    # 5 V buck, rear-right
    'C101': (63.2, 65.8, 0), 'C102': (75.0, 64.5, 0), 'U101': (80.0, 56.0, 0), 'D103': (82.0, 66.0, 180),
    'L101': (96.0, 56.0, 90), 'C103': (94.0, 68.0, 0), 'C104': (88.0, 68.5, 0),
}


def bridge(side):
    """Left bridge in board coords; the right bridge mirrors it about x = W/2."""
    b = 400 if side == 'L' else 500
    t = {
        # BTS rotated 180 deg: tab (OUT) faces the motor terminals, logic pins face the DevKit
        'U%d' % (b + 1): (19.0, 8.5, 180), 'U%d' % (b + 2): (19.0, 22.0, 180),
        'J%d' % (b + 1): (5.4, 10.5, 270), 'J%d' % (b + 2): (5.4, 22.5, 270),
        'C%d' % (b + 7): (6.0, 36.0, 0), 'C%d' % (b + 8): (19.0, 36.0, 0),
        # VS decoupling next to pin 7
        'C%d' % (b + 2): (30.5, 4.0, 90), 'C%d' % (b + 3): (32.7, 4.0, 90),
        'C%d' % (b + 5): (30.5, 17.5, 90), 'C%d' % (b + 6): (32.7, 17.5, 90),
    }
    for half, y0 in ((0, 4.0), (1, 17.5)):
        r = b + 1 + 5 * half
        t['R%d' % r] = (35.5, y0, 0)              # IN 10k
        t['R%d' % (r + 1)] = (35.5, y0 + 2.5, 0)  # INH 10k
        t['R%d' % (r + 2)] = (35.5, y0 + 5.0, 0)  # SR 5.1k
        t['R%d' % (r + 3)] = (35.5, y0 + 7.5, 0)  # IS 470R
    if side == 'R':
        # terminals mirror with reversed pad order, so shift them to keep the same footprint area
        out = {k: (W - x, y + (5.08 if k.startswith('J') else 0), {0: 180, 180: 0, 90: 270, 270: 90}[a])
               for k, (x, y, a) in t.items()}
        # rotating (not mirroring) the BTS puts VS pin 7 at the bottom on this side: keep its caps at pin 7
        out['C%d' % (b + 2)] = (W - 30.7, 13.4, 90)
        out['C%d' % (b + 3)] = (W - 32.7, 13.4, 90)
        out['C%d' % (b + 5)] = (W - 30.7, 26.9, 90)
        out['C%d' % (b + 6)] = (W - 32.7, 26.9, 90)
        return out
    return t


PL.update(bridge('L'))
PL.update(bridge('R'))


# ref -> (proxy model, replace library model?)
# ref -> (step file in pcb/3d, replace library model?, rotation xyz deg, offset xyz mm)
PROXY = {'J101': ('XT60_male_vertical', True, (0, 0, 180), (3.265, 0, 8.1)),   # user-supplied XT60 model
         'F101': ('ATO_holder_with_fuse_envelope', True, (0, 0, 0), (0, 0, 0)),
         'J201': ('ESP32_DevKit38_on_sockets_envelope', False, (0, 0, 0), (0, 0, 0))}


def main():
    net = parse(open(os.path.join(PCB_DIR, 'racebot_main.net'), encoding='utf8').read())[0]
    comps = find(find(net, 'components')[0], 'comp')
    nets = find(find(net, 'nets')[0], 'net')
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)

    netinfo = {}
    for n in nets:
        name = find(n, 'name')[0][1]
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni
    padnet = {}
    for n in nets:
        name = find(n, 'name')[0][1]
        for nd in find(n, 'node'):
            padnet[(find(nd, 'ref')[0][1], find(nd, 'pin')[0][1])] = name

    missing = []
    for c in comps:
        ref = find(c, 'ref')[0][1]
        val = find(c, 'value')[0][1]
        fpid = find(c, 'footprint')[0][1]
        lib, name = fpid.split(':', 1)
        fp = pcbnew.FootprintLoad(os.path.join(FPLIB, lib + '.pretty'), name)
        fp.SetFPIDAsString(fpid)
        fp.SetReference(ref)
        fp.SetValue(val)
        sp = find(c, 'sheetpath')[0]
        tst = find(sp, 'tstamps')[0][1]
        ctst = find(c, 'tstamps')[0][1]
        fp.SetPath(pcbnew.KIID_PATH(tst + ctst))
        fp.SetSheetname(find(sp, 'names')[0][1])
        for key, fname in (('description', 'Description'), ('datasheet', 'Datasheet')):
            v = find(c, key)
            if v and fp.GetField(fname):
                fp.GetField(fname).SetText(v[0][1])
        for fld in (find(find(c, 'fields')[0], 'field') if find(c, 'fields') else []):
            fname = find(fld, 'name')[0][1]
            fval = fld[-1] if isinstance(fld[-1], str) else ''
            if fname in ('LCSC', 'MPN', 'Note'):
                fp.SetField(fname, fval)
                f = fp.GetField(fname)
                if f:
                    f.SetVisible(False)
        if ref not in PL:
            missing.append(ref)
            x, y, a = 140.0, 120.0, 0
        else:
            x, y, a = PL[ref]
        if ref in PROXY:
            if PROXY[ref][1]:
                fp.Models().clear()
            m = pcbnew.FP_3DMODEL()
            m.m_Filename = '${KIPRJMOD}/3d/' + PROXY[ref][0] + '.step'
            m.m_Rotation = pcbnew.VECTOR3D(*PROXY[ref][2])
            m.m_Offset = pcbnew.VECTOR3D(*PROXY[ref][3])
            fp.Models().append(m)
        board.Add(fp)
        fp.SetPosition(P(x, y))
        fp.SetOrientationDegrees(a)
        for pad in fp.Pads():
            k = (ref, pad.GetNumber())
            if k in padnet:
                pad.SetNet(netinfo[padnet[k]])
    if missing:
        print('UNPLACED:', missing)

    # board outline
    rect = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_RECTANGLE)
    rect.SetLayer(pcbnew.Edge_Cuts)
    rect.SetStart(P(0, 0))
    rect.SetEnd(P(W, H))
    rect.SetWidth(mm(0.1))
    board.Add(rect)

    # M3 mounting holes (+ matching circles on Dwgs.User for the DXF hand-off)
    holes = [(HOLE_INSET, HOLE_INSET), (W - HOLE_INSET, HOLE_INSET),
             (HOLE_INSET, H - HOLE_INSET), (W - HOLE_INSET, H - HOLE_INSET)]
    for i, (x, y) in enumerate(holes):
        fp = pcbnew.FootprintLoad(os.path.join(FPLIB, 'MountingHole.pretty'), 'MountingHole_3.2mm_M3')
        fp.SetFPIDAsString('MountingHole:MountingHole_3.2mm_M3')
        fp.SetReference('H%d' % (i + 1))
        fp.SetValue('M3')
        fp.Reference().SetVisible(False)
        fp.SetBoardOnly(True)
        fp.SetExcludedFromBOM(True)
        fp.SetExcludedFromPosFiles(True)
        board.Add(fp)
        fp.SetPosition(P(x, y))
        c = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_CIRCLE)
        c.SetLayer(pcbnew.Dwgs_User)
        c.SetCenter(P(x, y))
        c.SetEnd(P(x + 1.6, y))
        c.SetWidth(mm(0.1))
        board.Add(c)

    # ESP32 DevKit body outline + antenna keep-out reminder (Dwgs.User / F.Fab)
    for layer in (pcbnew.User_1, pcbnew.F_Fab):
        r = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_RECTANGLE)
        r.SetLayer(layer)
        r.SetStart(P(54 - 14.2, 2 - 7.6))
        r.SetEnd(P(54 + 14.2, 2 - 7.6 + 55.0))
        r.SetWidth(mm(0.15))
        board.Add(r)
    ant = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_RECTANGLE)
    ant.SetLayer(pcbnew.User_1)
    ant.SetStart(P(54 - 9, 2 - 7.6))
    ant.SetEnd(P(54 + 9, 2 - 7.6 + 6.5))
    ant.SetWidth(mm(0.15))
    board.Add(ant)
    for txt, x, y, layer in (('ESP32 DEVKIT (38-pin) - ANTENNA OVERHANGS FRONT', 54, -3, pcbnew.User_1),
                             ('L', 2, 31, pcbnew.F_SilkS), ('R', W - 2, 31, pcbnew.F_SilkS),
                             ('BATT - +', 23.6, 75, pcbnew.F_SilkS), ('SW', 42.4, 75, pcbnew.F_SilkS),
                             ('ELRS', 69.5, 46, pcbnew.F_SilkS)):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(txt)
        t.SetLayer(layer)
        t.SetPosition(P(x, y))
        t.SetTextSize(pcbnew.VECTOR2I(mm(1.2), mm(1.2)))
        t.SetTextThickness(mm(0.18))
        board.Add(t)

    # mech origin = rear-left board corner (used by DXF --udo and STEP --user-origin)
    ds.SetAuxOrigin(P(0, H))
    ds.SetGridOrigin(P(0, H))
    out = os.path.join(PCB_DIR, 'racebot_main.kicad_pcb')
    board.Save(out)
    print('saved', out, len(comps), 'footprints')


main()
