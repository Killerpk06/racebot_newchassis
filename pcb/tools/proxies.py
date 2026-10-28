"""Envelope (proxy) STEP models for parts that have no KiCad 3D model.

Boxes are given in footprint coordinates (x right, y down, z up, mm); KiCad's 3D
space has +Y up, so y is negated on export.
"""
import os, sys
import cadquery as cq

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)


def box(x0, x1, y0, y1, z0, z1):
    ya, yb = -y1, -y0
    return cq.Workplane('XY').box(x1 - x0, yb - ya, z1 - z0, centered=False).translate((x0, ya, z0))


def save(name, *solids):
    w = solids[0]
    for s in solids[1:]:
        w = w.union(s)
    cq.exporters.export(w, os.path.join(OUT, name + '.step'))
    bb = w.val().BoundingBox()
    print(name, 'z max %.1f' % bb.zmax)


# AMASS XT60PW horizontal: ~15.8 W x 8.4 H body, mating face toward footprint -Y
save('XT60PW-M_envelope', box(-4.3, 11.5, -16.4, 2.2, 0, 8.4))
save('XT60PW-F_envelope', box(-11.5, 4.3, -16.4, 2.2, 0, 8.4))
# Littelfuse FLR 178.6165 ATO holder + fitted ATO blade fuse (19.1 x 5.1 head)
save('ATO_holder_with_fuse_envelope',
     box(-3.8, 16.6, -2.0, 4.5, 0, 13.0),
     box(6.4 - 9.55, 6.4 + 9.55, 1.25 - 2.55, 1.25 + 2.55, 13.0, 24.0))
# ESP32 38-pin DevKit (28.3 x 55.0) sitting on 8.5 mm female headers, referenced to J201 pin 1
save('ESP32_DevKit38_on_sockets_envelope',
     box(12.7 - 14.15, 12.7 + 14.15, -7.6, 47.4, 8.5, 10.1),          # devkit PCB
     box(12.7 - 9.0, 12.7 + 9.0, -7.6, 17.9, 10.1, 13.3),             # WROOM module + shield
     box(12.7 - 4.0, 12.7 + 4.0, 41.9, 48.4, 10.1, 13.1))             # micro-USB
