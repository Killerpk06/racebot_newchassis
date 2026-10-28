"""Rasterise the copper of the power nets (filled pours + pads + tracks + vias, per layer) and the
end-point pads of each power path, for neck_width.py.  Run with KiCad's python.

usage: neck_raster.py board.kicad_pcb out.npz
"""
import sys
import numpy as np
import pcbnew
from PIL import Image, ImageDraw

RES = 0.05                                   # mm per pixel
b = pcbnew.LoadBoard(sys.argv[1])
T = pcbnew.ToMM
bb = b.GetBoardEdgesBoundingBox()
X0, Y0 = T(bb.GetX()), T(bb.GetY())
NX, NY = int(T(bb.GetWidth()) / RES) + 1, int(T(bb.GetHeight()) / RES) + 1
LAY = {'F': pcbnew.F_Cu, 'B': pcbnew.B_Cu}


def px(v):
    return ((T(v.x) - X0) / RES, (T(v.y) - Y0) / RES)


def new():
    return Image.new('1', (NX, NY), 0)


def draw_polyset(d, ps):
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i)
        d.polygon([px(o.CPoint(k)) for k in range(o.PointCount())], fill=1)
        for h in range(ps.HoleCount(i)):
            hh = ps.Hole(i, h)
            d.polygon([px(hh.CPoint(k)) for k in range(hh.PointCount())], fill=0)


def copper(net, lc):
    lay = LAY[lc]
    img = new(); d = ImageDraw.Draw(img)
    for z in b.Zones():
        if z.GetNetname() == net and z.IsOnLayer(lay) and not z.GetIsRuleArea():
            draw_polyset(d, z.GetFilledPolysList(lay))
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() == net and p.IsOnLayer(lay):
                draw_polyset(d, p.GetEffectivePolygon(lay))
    for t in b.GetTracks():
        if t.GetNetname() != net:
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            x, y = px(t.GetPosition()); r = T(t.GetWidth(lay)) / 2 / RES
            d.ellipse([x - r, y - r, x + r, y + r], fill=1)
        elif t.GetLayer() == lay:
            w = T(t.GetWidth()) / RES
            (ax, ay), (bx, by) = px(t.GetStart()), px(t.GetEnd())
            d.line([(ax, ay), (bx, by)], fill=1, width=max(1, int(round(w))))
            for cx, cy in ((ax, ay), (bx, by)):
                d.ellipse([cx - w / 2, cy - w / 2, cx + w / 2, cy + w / 2], fill=1)
    return np.array(img, dtype=bool)


def pads(spec, lc):
    """spec: 'REF.PAD[,REF.PAD...]' or 'VIAS:x0,y0,x1,y1' (GND vias inside a board-coordinate box)."""
    lay = LAY[lc]
    img = new(); d = ImageDraw.Draw(img)
    if spec.startswith('VIAS:'):
        x0, y0, x1, y1 = [float(v) for v in spec[5:].split(',')]
        for t in b.GetTracks():
            if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == 'GND':
                x, y = T(t.GetPosition().x) - 100, T(t.GetPosition().y) - 100
                if x0 <= x <= x1 and y0 <= y <= y1:
                    cx, cy = px(t.GetPosition()); r = T(t.GetWidth(lay)) / 2 / RES
                    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=1)
    else:
        for item in spec.split(','):
            ref, num = item.split('.')
            for p in b.FindFootprintByReference(ref).Pads():
                if p.GetNumber() == num and p.IsOnLayer(lay):
                    draw_polyset(d, p.GetEffectivePolygon(lay))
    a = np.array(img, dtype=bool)
    assert a.any(), spec
    return a


L, R = '/Motor Bridge L/', '/Motor Bridge R/'
PATHS = [
    # name, net, layer, source, target
    ('VMOT  J102 -> U401.7 (VS)', 'VMOT', 'F', 'J102.1', 'U401.7'),
    ('VMOT  J102 -> U402.7 (VS)', 'VMOT', 'F', 'J102.1', 'U402.7'),
    ('VMOT  J102 -> U501.7 (VS)', 'VMOT', 'F', 'J102.1', 'U501.7'),
    ('VMOT  J102 -> U502.7 (VS)', 'VMOT', 'F', 'J102.1', 'U502.7'),
    ('VMOT  J102 -> U101.1 (buck VIN)', 'VMOT', 'F', 'J102.1', 'U101.1'),
    ('BAT_POS J101+ -> F101', '/Power/BAT_POS', 'F', 'J101.2', 'F101.1'),
    ('VBAT_F  F101 -> J102 (switch)', '/Power/VBAT_F', 'F', 'F101.2', 'J102.2'),
    ('BAT_NEG J101- -> Q101 drain', '/Power/BAT_NEG', 'F', 'J101.1', 'Q101.5'),
    ('GND   Q101 source -> island vias (F)', 'GND', 'F', 'Q101.1,Q101.2,Q101.3', 'VIAS:6.6,57.4,23.4,67.2'),
    ('GND   U401.1 -> island vias (F)', 'GND', 'F', 'U401.1', 'VIAS:12.8,16.3,30.1,28.2'),
    ('GND   U402.1 -> island vias (F)', 'GND', 'F', 'U402.1', 'VIAS:12.8,37.5,29.5,44.0'),
    ('GND   U501.1 -> island vias (F)', 'GND', 'F', 'U501.1', 'VIAS:78.75,0.5,101.2,7.7'),
    ('GND   U502.1 -> island vias (F)', 'GND', 'F', 'U502.1', 'VIAS:78.1,16.7,96.0,28.9'),
    ('GND   plane Q101 -> U401 island (B)', 'GND', 'B', 'VIAS:6.6,57.4,23.4,67.2', 'VIAS:12.8,16.3,30.1,28.2'),
    ('GND   plane Q101 -> U402 island (B)', 'GND', 'B', 'VIAS:6.6,57.4,23.4,67.2', 'VIAS:12.8,37.5,29.5,44.0'),
    ('GND   plane Q101 -> U501 island (B)', 'GND', 'B', 'VIAS:6.6,57.4,23.4,67.2', 'VIAS:78.75,0.5,101.2,7.7'),
    ('GND   plane Q101 -> U502 island (B)', 'GND', 'B', 'VIAS:6.6,57.4,23.4,67.2', 'VIAS:78.1,16.7,96.0,28.9'),
    ('L_OUT_A U401 tab -> J401.1 (F)', L + 'L_OUT_A', 'F', 'U401.8', 'J401.1'),
    ('L_OUT_A J401.1 -> J402.1 (B)', L + 'L_OUT_A', 'B', 'J401.1', 'J402.1'),
    ('L_OUT_B U402 tab -> J402.2 (F)', L + 'L_OUT_B', 'F', 'U402.8', 'J402.2'),
    ('L_OUT_B U402 tab -> J401.2 (F)', L + 'L_OUT_B', 'F', 'U402.8', 'J401.2'),
    ('R_OUT_A U501 tab -> J501.2 (F)', R + 'R_OUT_A', 'F', 'U501.8', 'J501.2'),
    ('R_OUT_A J501.2 -> J502.2 (B)', R + 'R_OUT_A', 'B', 'J501.2', 'J502.2'),
    ('R_OUT_B U502 tab -> J502.1 (F)', R + 'R_OUT_B', 'F', 'U502.8', 'J502.1'),
    ('R_OUT_B U502 tab -> J501.1 (F)', R + 'R_OUT_B', 'F', 'U502.8', 'J501.1'),
]
out = {'res': np.array(RES), 'names': np.array([p[0] for p in PATHS])}
cache = {}
for i, (name, net, lc, s, t) in enumerate(PATHS):
    if (net, lc) not in cache:
        cache[(net, lc)] = copper(net, lc)
    out['c%d' % i] = cache[(net, lc)]
    out['s%d' % i] = pads(s, lc)
    out['t%d' % i] = pads(t, lc)
np.savez_compressed(sys.argv[2], **out)
print('rasterised', len(PATHS), 'paths at', RES, 'mm')
