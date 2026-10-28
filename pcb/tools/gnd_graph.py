"""Union-find over GND copper fragments (all GND zones, both layers) joined by vias, THT pads and GND tracks."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
from layout_v2 import *
b = pcbnew.LoadBoard(sys.argv[1])
frags = []
for z in b.Zones():
    if z.GetNetname() != 'GND': continue
    for L in (pcbnew.F_Cu, pcbnew.B_Cu):
        if not z.IsOnLayer(L): continue
        ps = z.GetFilledPolysList(L)
        for i in range(ps.OutlineCount()):
            frags.append((z.GetZoneName(), L, ps, i))
par = list(range(len(frags)))
def f(a):
    while par[a] != a: par[a] = par[par[a]]; a = par[a]
    return a
def at(pt, L):
    return [k for k, (n, l, ps, i) in enumerate(frags) if l == L and ps.Contains(pt, i)]
def join(ks):
    for k in ks[1:]: par[f(k)] = f(ks[0])
for t in b.GetTracks():
    if t.GetNetname() != 'GND': continue
    if t.Type() == pcbnew.PCB_VIA_T:
        join(at(t.GetPosition(), pcbnew.F_Cu) + at(t.GetPosition(), pcbnew.B_Cu))
    else:
        join(at(t.GetStart(), t.GetLayer()) + at(t.GetEnd(), t.GetLayer()))
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetNetname() != 'GND': continue
        ks = []
        for L in (pcbnew.F_Cu, pcbnew.B_Cu):
            if p.IsOnLayer(L): ks += at(p.GetPosition(), L)
        join(ks)
groups = {}
for k in range(len(frags)): groups.setdefault(f(k), []).append(k)
for g, ks in groups.items():
    if len(ks) > 20: print('main group', len(ks)); continue
    for k in ks:
        n, L, ps, i = frags[k]; o = ps.Outline(i); bb = o.BBox()
        print('ISOLATED', n, b.GetLayerName(L), [round(v, 1) for v in bxy(bb.GetPosition()) + bxy(bb.GetEnd())], round(o.Area() / 1e12, 2))
