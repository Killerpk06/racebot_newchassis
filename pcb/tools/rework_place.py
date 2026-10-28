"""Layout v2, step 1: place parts, add fixed copper + routing keep-outs, export a Specctra DSN for
Freerouting with the power nets (carried by pours) taken out of the routing job.

usage: python rework_place.py <pcb dir>
"""
import os, re, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
from layout_v2 import *

D = sys.argv[1]
PCB = os.path.join(D, 'racebot_main.kicad_pcb')
write_stackup(PCB)
board = pcbnew.LoadBoard(PCB)
nets = board.GetNetsByName()

# ---- clean slate: copper, zones, old free texts
for t in list(board.GetTracks()):
    board.Delete(t)
for z in list(board.Zones()):
    board.Delete(z)
for d in list(board.GetDrawings()):
    if d.GetClass() == 'PCB_TEXT' and d.GetLayer() == pcbnew.F_SilkS:
        board.Delete(d)

# ---- placement
for ref, (x, y, a) in PLACE.items():
    f = board.FindFootprintByReference(ref)
    f.SetOrientationDegrees(a)
    f.SetPosition(P(x, y))
place_c101(board)
board.FindFootprintByReference('U101').SetDuplicatePadNumbersAreJumpers(True)
for f in board.GetFootprints():
    f.BuildCourtyardCaches()


def add_track(x0, y0, x1, y1, w, layer, net, locked=True):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(P(x0, y0)); t.SetEnd(P(x1, y1))
    t.SetWidth(mm(w)); t.SetLayer(layer_id(layer)); t.SetNet(nets[net]); t.SetLocked(locked)
    board.Add(t)


def add_via(x, y, net, size, drill, locked=True):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(P(x, y)); v.SetWidth(mm(size)); v.SetDrill(mm(drill)); v.SetNet(nets[net]); v.SetLocked(locked)
    board.Add(v)
    return v


# ---- BTS signal fan-out: pad -> short stub -> via under the package body
for ref, vx in FANOUT_X.items():
    f = board.FindFootprintByReference(ref)
    for p in f.Pads():
        if p.GetNumber() in ('2', '3', '5', '6'):
            x, y = bxy(p.GetPosition())
            add_track(STUB_FROM[ref], y, vx, y, 0.3, 'F', p.GetNetname())
            add_via(vx, y, p.GetNetname(), 0.6, 0.3)

# BTS pin 4 (OUT) -> tab link, placed now so the router keeps clear of it
for ref in FANOUT_X:
    f = board.FindFootprintByReference(ref)
    p4 = [p for p in f.Pads() if p.GetNumber() == '4'][0]
    tab = [p for p in f.Pads() if p.GetNumber() == '8'][0]
    (x4, y4), (xt, _) = bxy(p4.GetPosition()), bxy(tab.GetPosition())
    add_track(x4, y4, xt, y4, 0.8, 'F', p4.GetNetname())

for x0, y0, x1, y1, w, l, n in FIXED_TRACKS:
    add_track(x0, y0, x1, y1, w, l, n)
for x, y, n, s, d in FIXED_SIGNAL_VIAS + FIXED_VIAS:
    add_via(x, y, n, s, d)

# ---- a GND via for every SMD ground pad of the logic parts (zones are not part of the routing job)
LOGIC = (39.7, 0.3, 68.3, 49.4)
placed = []


def clear_spot(x, y, r, own_pad):
    pt = P(x, y)
    if not (LOGIC[0] + 0.6 < x < LOGIC[2] - 0.6 and LOGIC[1] + 0.6 < y < LOGIC[3] - 0.6):
        return False
    for f in board.GetFootprints():
        for p in f.Pads():
            if p.m_Uuid.AsString() == own_pad:
                continue
            if p.HitTest(pt, mm(r + 0.32)):
                return False
        if f.GetReference() not in ('J201', 'J202'):
            c = f.GetCourtyard(pcbnew.F_CrtYd)
            if c.OutlineCount() and c.Contains(pt) and not any(q.m_Uuid.AsString() == own_pad for q in f.Pads()):
                return False
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            if (t.GetPosition() - pt).EuclideanNorm() < mm(r + t.GetWidth(pcbnew.F_Cu) / 2e6 + 0.32):
                return False
        elif t.HitTest(pt, mm(r + 0.32) + t.GetWidth() // 2):
            return False
    return True


n_logic = 0
for f in board.GetFootprints():
    fx, fy = bxy(f.GetPosition())
    if not (LOGIC[0] < fx < LOGIC[2] and LOGIC[1] < fy < LOGIC[3]) or f.GetReference() in ('J201', 'J202'):
        continue
    for p in f.Pads():
        if p.GetNetname() != 'GND' or p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
            continue
        px, py = bxy(p.GetPosition())
        # try outward from the footprint centre first, then the other directions
        base = math.atan2(py - fy, px - fx) if (px, py) != (fx, fy) else 0.0
        done = False
        for d in (1.15, 1.4, 1.7, 2.0):
            for k in (0, 1, -1, 2, -2, 3, -3, 4):
                a = base + k * math.pi / 4
                x, y = px + d * math.cos(a), py + d * math.sin(a)
                if clear_spot(x, y, 0.3, p.m_Uuid.AsString()):
                    add_track(px, py, x, y, 0.3, 'F', 'GND')
                    add_via(x, y, 'GND', 0.6, 0.3)
                    n_logic += 1
                    done = True
                    break
            if done:
                break
        if not done:
            print('no GND via spot for', f.GetReference(), p.GetNumber())
print('logic GND vias', n_logic)


# ---- routing keep-outs
def keepout(poly, layer):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetLayer(layer_id(layer))
    z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True)
    z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    z.SetDoNotAllowZoneFills(False)
    z.SetZoneName('ROUTE_KEEPOUT')
    o = z.Outline(); o.NewOutline()
    for x, y in poly:
        o.Append(mm(OX + x), mm(OY + y))
    board.Add(z)


for r in KEEP_F:
    keepout(r, 'F')
for r in KEEP_B:
    keepout(r, 'B')

board.Save(PCB)
set_netclasses(os.path.join(D, 'racebot_main.kicad_pro'))
board = pcbnew.LoadBoard(PCB)
dsn = os.path.join(D, 'racebot_main.dsn')
print('DSN export:', pcbnew.ExportSpecctraDSN(board, dsn))

# ---- take the pour-carried nets out of the routing job (their pads/vias stay as obstacles)
s = open(dsn, encoding='utf8').read()
n = 0
for name in POWER_NETS:
    pat = re.compile(r'(\(net "?%s"?\s*\n\s*)\(pins[^)]*\)' % re.escape(name))
    s, k = pat.subn(r'\1', s)
    n += k
# F.Cu keep-outs stop Freerouting cold; model the protected F.Cu areas as fixed VMOT copper instead
ko = re.compile(r'    \(keepout "" \(polygon F\.Cu 0 (.*?)\)\)\n', re.S)
polys = [m.group(1) for m in ko.finditer(s)]
s = ko.sub('', s)
s = s.replace('  (wiring\n', '  (wiring\n' + ''.join('    (wire (polygon F.Cu 0 %s)(net VMOT)(type fix))\n'
                                                      % ' '.join(p.split()) for p in polys), 1)
open(dsn, 'w', encoding='utf8').write(s)
print('power nets stripped from routing:', n, 'of', len(POWER_NETS), '; F.Cu keep-outs as fixed copper:', len(polys))
