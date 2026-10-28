"""Re-place every reference designator so no silkscreen overlaps pads, other silk or the board edge.
A reference that has no free spot moves to F.Fab (still in the assembly drawing, not printed).

usage: silk_fix.py board.kicad_pcb
"""
import sys
import pcbnew

b = pcbnew.LoadBoard(sys.argv[1])
T, mm = pcbnew.ToMM, pcbnew.FromMM
bb = b.GetBoardEdgesBoundingBox()
BX0, BY0, BX1, BY1 = T(bb.GetX()), T(bb.GetY()), T(bb.GetRight()), T(bb.GetBottom())


def box(item, grow=0.0):
    r = item.GetBoundingBox()
    return (T(r.GetX()) - grow, T(r.GetY()) - grow, T(r.GetRight()) + grow, T(r.GetBottom()) + grow)


def hit(a, c):
    return a[0] < c[2] and c[0] < a[2] and a[1] < c[3] and c[1] < a[3]


obst = []
for f in b.GetFootprints():
    for p in f.Pads():
        if p.IsOnLayer(pcbnew.F_Mask) or p.IsOnLayer(pcbnew.F_Cu):
            obst.append(box(p, 0.2))
    for g in f.GraphicalItems():
        if g.GetLayer() == pcbnew.F_SilkS and g.GetClass() != 'PCB_FIELD':
            obst.append(box(g, 0.15))
for d in b.GetDrawings():
    if d.GetLayer() == pcbnew.F_SilkS:
        obst.append(box(d, 0.25))

moved = fab = 0
order = sorted(b.GetFootprints(), key=lambda f: -T(f.GetBoundingBox(False).GetWidth()) * T(f.GetBoundingBox(False).GetHeight()))
for f in order:
    ref = f.Reference()
    if f.GetReference().startswith('H') or not ref.IsVisible():
        continue
    ref.SetLayer(pcbnew.F_SilkS)
    ref.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
    ref.SetTextThickness(mm(0.12))
    ref.SetKeepUpright(True)
    ref.SetTextAngleDegrees(0)
    c = f.GetCourtyard(pcbnew.F_CrtYd)
    cb = c.BBox() if c.OutlineCount() else f.GetBoundingBox(False)
    x0, y0, x1, y1 = T(cb.GetX()), T(cb.GetY()), T(cb.GetRight()), T(cb.GetBottom())
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    cands = [(cx, y0 - 0.7), (cx, y1 + 0.7), (x0 - 0.3, cy), (x1 + 0.3, cy),
             (x0, y0 - 0.7), (x1, y0 - 0.7), (x0, y1 + 0.7), (x1, y1 + 0.7), (cx, cy)]
    for ang in (0, 90):
        ref.SetTextAngleDegrees(ang)
        best = None
        for (x, y) in cands:
            for dx, dy in ((0, 0), (0.6, 0), (-0.6, 0), (0, 0.6), (0, -0.6), (1.2, 0), (-1.2, 0)):
                ref.SetTextPos(pcbnew.VECTOR2I(mm(x + dx), mm(y + dy)))
                tb = box(ref, 0.1)
                if tb[0] < BX0 + 0.3 or tb[1] < BY0 + 0.3 or tb[2] > BX1 - 0.3 or tb[3] > BY1 - 0.3:
                    continue
                if any(hit(tb, o) for o in obst):
                    continue
                best = tb
                break
            if best:
                break
        if best:
            break
    if best:
        obst.append(best)
        moved += 1
    else:
        ref.SetTextAngleDegrees(0)
        ref.SetTextPos(pcbnew.VECTOR2I(mm(cx), mm(cy)))
        ref.SetLayer(pcbnew.F_Fab)
        fab += 1
b.Save(sys.argv[1])
print('references placed on silk: %d, moved to F.Fab: %d' % (moved, fab))
