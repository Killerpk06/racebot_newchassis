"""After SES import: drop router copper on pour-only nets and signal copper that strays into the
protected F.Cu power areas, then clean dangling stubs.  usage: fix_routes.py board.kicad_pcb"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
from layout_v2 import *
b = pcbnew.LoadBoard(sys.argv[1])
OK = [(39.5, 0, 68.5, 49.6), (56.6, 59.1, 79.2, H)] + WINDOWS_F
def inside(x, y): return any(a <= x <= c and q <= y <= d for a, q, c, d in OK)
def seg_ok(t):
    (x0, y0), (x1, y1) = bxy(t.GetStart()), bxy(t.GetEnd())
    return all(inside(x0 + (x1 - x0) * k / 20, y0 + (y1 - y0) * k / 20) for k in range(21))
gone = 0
for t in list(b.GetTracks()):
    if t.IsLocked():
        continue
    if t.GetNetname() in POWER_NETS:
        b.Delete(t); gone += 1
    elif t.Type() == pcbnew.PCB_VIA_T:
        if not inside(*bxy(t.GetPosition())):
            b.Delete(t); gone += 1
    elif t.GetLayer() == pcbnew.F_Cu and not seg_ok(t):
        b.Delete(t); gone += 1
# dangling clean-up (unlocked only)
def endpoints_ok(t, items, pads):
    for e in (t.GetStart(), t.GetEnd()):
        hit = False
        for o in items:
            if o is t or o.GetNetname() != t.GetNetname() or o.m_Uuid.AsString() == t.m_Uuid.AsString():
                continue
            if o.Type() == pcbnew.PCB_VIA_T:
                hit = (o.GetPosition() - e).EuclideanNorm() < mm(0.05)
            elif o.GetLayer() == t.GetLayer():
                hit = o.HitTest(e, mm(0.02))
            if hit: break
        if not hit:
            hit = any(n == t.GetNetname() and p.IsOnLayer(t.GetLayer()) and p.HitTest(e, mm(0.01)) for p, n in pads)
        if not hit:
            return False
    return True
pads = [(p, p.GetNetname()) for f in b.GetFootprints() for p in f.Pads()]
while True:
    items = list(b.GetTracks())
    dead = [t for t in items if not t.IsLocked() and t.Type() != pcbnew.PCB_VIA_T and not endpoints_ok(t, items, pads)]
    vias = [v for v in items if v.Type() == pcbnew.PCB_VIA_T and not v.IsLocked() and
            sum(1 for o in items if o.Type() != pcbnew.PCB_VIA_T and o.GetNetname() == v.GetNetname()
                and (o.GetStart() == v.GetPosition() or o.GetEnd() == v.GetPosition())) < 2]
    if not dead and not vias: break
    for t in dead + vias: b.Delete(t); gone += 1
b.Save(sys.argv[1])
print('removed', gone)
