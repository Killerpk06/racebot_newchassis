import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
from layout_v2 import *
b = pcbnew.LoadBoard(sys.argv[1]); nets = b.GetNetsByName()
for net, x, y in [('/Motor Bridge R/R_B_INH', 84.7, 30.93), ('/Motor Bridge R/R_B_IS', 84.7, 34.74),
                  ('/Motor Bridge L/L_B_IS', 23.3, 31.66), ('/Motor Bridge R/R_B_SR', 84.7, 33.47)]:
    xs = 83.2 if x > 50 else 24.8
    t = pcbnew.PCB_TRACK(b); t.SetStart(P(xs, y)); t.SetEnd(P(x, y)); t.SetWidth(mm(0.3)); t.SetLayer(pcbnew.F_Cu)
    t.SetNet(nets[net]); t.SetLocked(True); b.Add(t)
    v = pcbnew.PCB_VIA(b); v.SetPosition(P(x, y)); v.SetWidth(mm(0.6)); v.SetDrill(mm(0.3)); v.SetNet(nets[net]); v.SetLocked(True); b.Add(v)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
z = [z for z in b.Zones() if z.GetZoneName() == 'GND_logic'][0]
fp = z.GetFilledPolysList(pcbnew.F_Cu)
vias = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == 'GND']
for i in range(fp.OutlineCount()):
    o = fp.Outline(i); bb = o.BBox()
    nv = sum(1 for v in vias if o.PointInside(v.GetPosition()))
    print('frag', i, [round(v, 1) for v in bxy(bb.GetPosition()) + bxy(bb.GetEnd())], 'vias', nv, 'area mm2', round(o.Area() / 1e12, 2))
b.Save(sys.argv[1]); write_stackup(sys.argv[1])
