"""List routed (unlocked) F.Cu signal tracks that leave the allowed F.Cu routing areas."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
from layout_v2 import *
b = pcbnew.LoadBoard(sys.argv[1])
OK = [(39.5, 0, 68.5, 49.6), (56.6, 59.1, 79.2, H)] + WINDOWS_F
def inside(x, y): return any(a <= x <= c and bb <= y <= d for a, bb, c, d in OK)
bad = {}
for t in b.GetTracks():
    if t.IsLocked() or t.GetLayer() != pcbnew.F_Cu or t.Type() == pcbnew.PCB_VIA_T: continue
    (x0, y0), (x1, y1) = bxy(t.GetStart()), bxy(t.GetEnd())
    n = 10
    if not all(inside(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n + 1)):
        bad.setdefault(t.GetNetname(), []).append((round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)))
bv = [(t.GetNetname(), bxy(t.GetPosition())) for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T and not t.IsLocked()
      and not inside(*bxy(t.GetPosition()))]
for k, v in bad.items(): print('TRACK', k, v)
for v in bv: print('VIA', v)
print('bad nets', len(bad), 'bad vias', len(bv))
