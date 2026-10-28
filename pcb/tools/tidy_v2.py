"""Remove unused fan-out vias/stubs; give every GND_logic fragment without a via one stitching via."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
from layout_v2 import *
b = pcbnew.LoadBoard(sys.argv[1]); nets = b.GetNetsByName()
tr = list(b.GetTracks())
gone = 0
kill = []
for v in [t for t in tr if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() not in POWER_NETS]:
    x, y = bxy(v.GetPosition())
    if abs(x - 23.3) > 0.01 and abs(x - 84.7) > 0.01:
        continue
    on_b = [t for t in tr if t.Type() != pcbnew.PCB_VIA_T and t.GetLayer() == pcbnew.B_Cu and t.GetNetname() == v.GetNetname()
            and (t.GetStart() == v.GetPosition() or t.GetEnd() == v.GetPosition())]
    if on_b:
        continue
    stubs = [t for t in tr if t.Type() != pcbnew.PCB_VIA_T and t.GetLayer() == pcbnew.F_Cu and t.GetNetname() == v.GetNetname()
             and (t.GetStart() == v.GetPosition() or t.GetEnd() == v.GetPosition())]
    kill.extend(stubs + [v])
for t in kill:
    b.Delete(t); gone += 1
print('removed unused fan-out items', gone)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
vias = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == 'GND']
added = 0
for z in b.Zones():
    if z.GetZoneName() != 'GND_logic':
        continue
    fp = z.GetFilledPolysList(pcbnew.F_Cu)
    for i in range(fp.OutlineCount()):
        o = fp.Outline(i)
        if any(o.PointInside(v.GetPosition()) for v in vias):
            continue
        # also connected if it touches a GND pad
        if any(p.GetNetname() == 'GND' and o.PointInside(p.GetPosition()) for f in b.GetFootprints() for p in f.Pads()):
            continue
        bb = o.BBox(); best = None
        for gx in range(bb.GetX(), bb.GetRight(), mm(0.1)):
            for gy in range(bb.GetY(), bb.GetBottom(), mm(0.1)):
                pt = pcbnew.VECTOR2I(gx, gy)
                if o.PointInside(pt) and o.SquaredDistance(pt) >= mm(0.45) ** 2:
                    best = pt; break
            if best: break
        if best:
            v = pcbnew.PCB_VIA(b); v.SetPosition(best); v.SetWidth(mm(0.6)); v.SetDrill(mm(0.3)); v.SetNet(nets['GND'])
            b.Add(v); added += 1
        print('fragment', bxy(bb.GetCenter()), 'via' if best else 'NO SPOT', bxy(best) if best else '')
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[1]); write_stackup(sys.argv[1]); set_netclasses(os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), 'racebot_main.kicad_pro'))
print('added', added)
