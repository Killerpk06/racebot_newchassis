"""Narrow +5V segments that miss 0.25 mm to a via; bridge isolated GND_logic fragments to the main B.Cu plane."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
from layout_v2 import *
b = pcbnew.LoadBoard(sys.argv[1]); nets = b.GetNetsByName()
vias = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
for t in b.GetTracks():
    if t.Type() != pcbnew.PCB_VIA_T and t.GetNetname() == '+5V' and not t.IsLocked():
        for v in vias:
            if v.GetNetname() != '+5V':
                gap = t.GetEffectiveShape().GetClearance(v.GetEffectiveShape(pcbnew.F_Cu))
                if gap < mm(0.25):
                    t.SetWidth(t.GetWidth() - 2 * (mm(0.25) - gap) - mm(0.02)); print('narrowed +5V to', pcbnew.ToMM(t.GetWidth()))
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
zb = [z for z in b.Zones() if z.GetZoneName() == 'GND_bottom'][0].GetFilledPolysList(pcbnew.B_Cu)
mi = max(range(zb.OutlineCount()), key=lambda i: zb.Outline(i).Area())
zf = [z for z in b.Zones() if z.GetZoneName() == 'GND_logic'][0].GetFilledPolysList(pcbnew.F_Cu)
gv = [v for v in vias if v.GetNetname() == 'GND']
def clr(q, ps, i, r):
    return ps.Contains(q, i) and all(ps.Contains(q + pcbnew.VECTOR2I(int(mm(r) * c), int(mm(r) * s)), i)
                                     for c, s in ((1, 0), (-1, 0), (0, 1), (0, -1), (.7, .7), (-.7, .7), (.7, -.7), (-.7, -.7)))
for fi in range(zf.OutlineCount()):
    if any(zf.Contains(v.GetPosition(), fi) and zb.Contains(v.GetPosition(), mi) for v in gv):
        continue
    bb = zf.Outline(fi).BBox(); ok = None
    for gy in range(bb.GetBottom(), bb.GetY(), -mm(0.1)):
        for gx in range(bb.GetX(), bb.GetRight(), mm(0.1)):
            q = pcbnew.VECTOR2I(gx, gy)
            if clr(q, zf, fi, 0.32) and clr(q, zb, mi, 0.32):
                ok = q; break
        if ok: break
    print('fragment', [round(x, 1) for x in bxy(bb.GetPosition()) + bxy(bb.GetEnd())], 'via', bxy(ok) if ok else 'NO SPOT')
    if ok:
        v = pcbnew.PCB_VIA(b); v.SetPosition(ok); v.SetWidth(mm(0.6)); v.SetDrill(mm(0.3)); v.SetNet(nets['GND']); b.Add(v)
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[1]); write_stackup(sys.argv[1])
