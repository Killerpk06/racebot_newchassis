"""Layout v2, step 2: import the Freerouting session, drop the routing keep-outs, add the pours,
BTS pin-4 -> tab links and stitching vias, tidy the silkscreen, refill and save.

usage: python rework_finish.py <pcb dir> [import]
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
from layout_v2 import *

D = sys.argv[1]
PCB = os.path.join(D, 'racebot_main.kicad_pcb')
board = pcbnew.LoadBoard(PCB)
nets = board.GetNetsByName()


def snap(t):
    is_via = t.Type() == pcbnew.PCB_VIA_T
    if is_via:
        return ('V', t.GetNetname(), bxy(t.GetPosition()), t.GetWidth(pcbnew.F_Cu), t.GetDrillValue())
    return ('T', t.GetNetname(), bxy(t.GetStart()), bxy(t.GetEnd()), t.GetWidth(), t.GetLayer())


def key(s):
    return (s[0], s[1]) + tuple(round(v, 2) for v in s[2]) + ((tuple(round(v, 2) for v in s[3]) + (s[5],)) if s[0] == 'T' else ())


if len(sys.argv) > 2 and sys.argv[2] == 'import':
    fixed = [snap(t) for t in board.GetTracks() if t.IsLocked()]
    ok = pcbnew.ImportSpecctraSES(board, os.path.join(D, 'racebot_main.ses'))
    print('SES import:', ok)
    have = set(key(snap(t)) for t in board.GetTracks())
    readd = 0
    for s in fixed:
        if key(s) in have:
            continue
        readd += 1
        if s[0] == 'V':
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(P(*s[2])); v.SetWidth(s[3]); v.SetDrill(s[4]); v.SetNet(nets[s[1]]); v.SetLocked(True)
            board.Add(v)
        else:
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(P(*s[2])); t.SetEnd(P(*s[3])); t.SetWidth(s[4]); t.SetLayer(s[5]); t.SetNet(nets[s[1]])
            t.SetLocked(True)
            board.Add(t)
    print('fixed items kept %d, re-added %d' % (len(fixed) - readd, readd))

# ---- routing keep-outs and any old pours go; pin-4 -> tab links (OUT nets are pour-only otherwise)
for z in list(board.Zones()):
    board.Delete(z)
for t in [t for t in board.GetTracks() if '_OUT_' in t.GetNetname()]:
    board.Delete(t)
for ref in ('U401', 'U402', 'U501', 'U502'):
    f = board.FindFootprintByReference(ref)
    p4 = [p for p in f.Pads() if p.GetNumber() == '4'][0]
    tab = [p for p in f.Pads() if p.GetNumber() == '8'][0]
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(p4.GetPosition()); t.SetEnd(pcbnew.VECTOR2I(tab.GetPosition().x, p4.GetPosition().y))
    t.SetWidth(mm(0.8)); t.SetLayer(pcbnew.F_Cu); t.SetNet(p4.GetNet()); t.SetLocked(True)
    board.Add(t)


def zone(name, netname, layer, prio, pts):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer_id(layer))
    z.SetNet(nets[netname])
    z.SetAssignedPriority(prio)
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetLocalClearance(mm(0.3))
    z.SetMinThickness(mm(0.25))
    z.SetZoneName(name)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    o = z.Outline(); o.NewOutline()
    for x, y in pts:
        o.Append(mm(OX + x), mm(OY + y))
    board.Add(z)


for zd in ZONES:
    zone(*zd)

# ---- stitching vias for the F.Cu ground areas (logic island, rear ELRS/LED area)


def clear_at(x, y, r, gap=0.35):
    pt = P(x, y)
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            lim = r + pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2 + (0.6 if t.GetNetname() == 'GND' else gap)
            if (t.GetPosition() - pt).EuclideanNorm() < mm(lim):
                return False
        elif t.HitTest(pt, mm(r + gap) + t.GetWidth() // 2):
            return False
    for f in board.GetFootprints():
        for p in f.Pads():
            if p.HitTest(pt, mm(r + gap + 0.1)):
                return False
            if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH) and \
                    (p.GetPosition() - pt).EuclideanNorm() < p.GetDrillSize().x // 2 + mm(r + 0.6):
                return False
    return True


def stitch(x0, y0, x1, y1, step, size=0.8, drill=0.4):
    n = 0
    gy = y0
    while gy <= y1:
        gx = x0
        while gx <= x1:
            if clear_at(gx, gy, size / 2):
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(P(gx, gy)); v.SetWidth(mm(size)); v.SetDrill(mm(drill)); v.SetNet(nets['GND'])
                board.Add(v)
                n += 1
            gx += step
        gy += step
    return n


print('stitching vias: logic %d, rear %d' % (stitch(43.8, 1.2, 64.4, 48.6, 3.0), stitch(57.8, 67.0, 78.0, 74.8, 3.0)))

filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())

# ---- free silkscreen texts
for d in list(board.GetDrawings()):
    if d.GetClass() == 'PCB_TEXT' and d.GetLayer() == pcbnew.F_SilkS:
        board.Delete(d)
for txt, x, y in (('L', 1.6, 42.0), ('R', W - 1.6, 42.0), ('BATT - +', 23.6, 75.0), ('SW', 46.0, 75.0),
                  ('ELRS', 66.4, 63.4), ('STAT 5V VM', 73.8, 68.6)):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(txt); t.SetLayer(pcbnew.F_SilkS); t.SetPosition(P(x, y))
    t.SetTextSize(pcbnew.VECTOR2I(mm(1.0), mm(1.0))); t.SetTextThickness(mm(0.15))
    board.Add(t)

board.Save(PCB)
write_stackup(PCB)
set_netclasses(os.path.join(D, 'racebot_main.kicad_pro'))
print('zones', len(list(board.Zones())), 'tracks+vias', len(list(board.GetTracks())))
