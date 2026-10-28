"""Find GND_logic fragments whose vias only land in small B.Cu islands; add a via into the main plane."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
from layout_v2 import *
b = pcbnew.LoadBoard(sys.argv[1]); nets = b.GetNetsByName()
zb = [z for z in b.Zones() if z.GetZoneName() == 'GND_bottom'][0].GetFilledPolysList(pcbnew.B_Cu)
main = max(range(zb.OutlineCount()), key=lambda i: zb.Outline(i).Area())
M = zb.Outline(main)
zf = [z for z in b.Zones() if z.GetZoneName() == 'GND_logic'][0].GetFilledPolysList(pcbnew.F_Cu)
vias = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == 'GND']
tht = [p for f in b.GetFootprints() for p in f.Pads() if p.GetNetname() == 'GND' and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH]
added = 0
for i in range(zf.OutlineCount()):
    o = zf.Outline(i)
    pts = [v.GetPosition() for v in vias if o.PointInside(v.GetPosition())] + [p.GetPosition() for p in tht if o.PointInside(p.GetPosition())]
    if any(M.PointInside(q) for q in pts):
        continue
    print('fragment', i, [round(v, 1) for v in bxy(o.BBox().GetPosition()) + bxy(o.BBox().GetEnd())], 'items', len(pts))
    bb = o.BBox(); done = False
    for gy in range(bb.GetY(), bb.GetBottom(), mm(0.1)):
        for gx in range(bb.GetX(), bb.GetRight(), mm(0.1)):
            q = pcbnew.VECTOR2I(gx, gy)
            if o.PointInside(q) and o.SquaredDistance(q) >= mm(0.32) ** 2 and M.PointInside(q) and M.SquaredDistance(q) >= mm(0.32) ** 2:
                v = pcbnew.PCB_VIA(b); v.SetPosition(q); v.SetWidth(mm(0.6)); v.SetDrill(mm(0.3)); v.SetNet(nets['GND']); b.Add(v)
                print('  via', bxy(q)); added += 1; done = True; break
        if done: break
    if not done: print('  NO SPOT')
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); b.Save(sys.argv[1]); write_stackup(sys.argv[1]); print('added', added)
