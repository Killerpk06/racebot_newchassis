import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
from layout_v2 import *
b = pcbnew.LoadBoard(sys.argv[1]); nets = b.GetNetsByName()
z = [z for z in b.Zones() if z.GetZoneName() == 'GND_logic'][0]
fp = z.GetFilledPolysList(pcbnew.F_Cu)
vias = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == 'GND']
gpads = [p for f in b.GetFootprints() for p in f.Pads() if p.GetNetname() == 'GND']
for i in range(fp.OutlineCount()):
    o = fp.Outline(i)
    if any(o.PointInside(v.GetPosition()) for v in vias): continue
    print('frag', i, 'pads inside', [p.GetParentFootprint().GetReference() + '.' + p.GetNumber() for p in gpads if o.PointInside(p.GetPosition())])
    bb = o.BBox(); done = False
    for gy in range(bb.GetY(), bb.GetBottom(), mm(0.1)):
        for gx in range(bb.GetX(), bb.GetRight(), mm(0.1)):
            pt = pcbnew.VECTOR2I(gx, gy)
            if o.PointInside(pt) and o.SquaredDistance(pt) >= mm(0.5) ** 2:
                v = pcbnew.PCB_VIA(b); v.SetPosition(pt); v.SetWidth(mm(0.6)); v.SetDrill(mm(0.3)); v.SetNet(nets['GND']); b.Add(v)
                print(' via at', bxy(pt)); done = True; break
        if done: break
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[1]); write_stackup(sys.argv[1])
