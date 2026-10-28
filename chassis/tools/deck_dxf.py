"""Write the racebot deck plate as a laser-cut DXF (mm, robot frame: +X right, +Y forward).

Same geometry as racebot_deck.SLDPRT. Run:  python deck_dxf.py <out.dxf>
"""
import math
import sys

ents = []


def line(x0, y0, x1, y1):
    ents.append(('LINE', x0, y0, x1, y1))


def arc(cx, cy, r, a0, a1):
    ents.append(('ARC', cx, cy, r, a0, a1))


def circle(cx, cy, d):
    ents.append(('CIRCLE', cx, cy, d / 2))


def rrect(x0, y0, x1, y1, r):
    line(x0 + r, y0, x1 - r, y0)
    line(x1, y0 + r, x1, y1 - r)
    line(x1 - r, y1, x0 + r, y1)
    line(x0, y1 - r, x0, y0 + r)
    arc(x1 - r, y0 + r, r, 270, 360)
    arc(x1 - r, y1 - r, r, 0, 90)
    arc(x0 + r, y1 - r, r, 90, 180)
    arc(x0 + r, y0 + r, r, 180, 270)


# outline 114 x 150, R4 corners
rrect(-57, -75, 57, 75, 4)
# MS L-clamp holes: 2 x 3, 29.8 apart, 5.2 / 11.2 / 17.2 mm in from the plate side edge
for s, ya in ((-1, 55.0), (-1, -27.0), (1, 27.0), (1, -55.0)):
    for d in (5.2, 11.2, 17.2):
        for dy in (-14.9, 14.9):
            circle(s * (57 - d), ya + dy, 3.2)
# PCB standoff holes: tap M3 (2.5 drill)
for x in (-50.5, 50.5):
    for y in (-64.5, 4.5):
        circle(x, y, 2.5)
# battery strap slots 22 x 3.5
for x in (-25, 25):
    for y in (12.75, 55.25):
        rrect(x - 11, y - 1.75, x + 11, y + 1.75, 1.7)
# lightening pockets
for x0, x1 in ((-36, -4), (4, 36)):
    rrect(x0, -58, x1, -4, 4)
    rrect(x0, 21, x1, 47, 4)
rrect(-30, 60, 30, 70, 4)

out = ['0', 'SECTION', '2', 'HEADER', '9', '$INSUNITS', '70', '4', '0', 'ENDSEC',
       '0', 'SECTION', '2', 'ENTITIES']
for e in ents:
    if e[0] == 'LINE':
        out += ['0', 'LINE', '8', 'CUT', '10', '%.4f' % e[1], '20', '%.4f' % e[2], '30', '0',
                '11', '%.4f' % e[3], '21', '%.4f' % e[4], '31', '0']
    elif e[0] == 'ARC':
        out += ['0', 'ARC', '8', 'CUT', '10', '%.4f' % e[1], '20', '%.4f' % e[2], '30', '0',
                '40', '%.4f' % e[3], '50', '%.4f' % e[4], '51', '%.4f' % e[5]]
    else:
        out += ['0', 'CIRCLE', '8', 'CUT', '10', '%.4f' % e[1], '20', '%.4f' % e[2], '30', '0',
                '40', '%.4f' % e[3]]
out += ['0', 'ENDSEC', '0', 'EOF']
open(sys.argv[1], 'w').write('\n'.join(out) + '\n')
print('wrote', len(ents), 'entities to', sys.argv[1])
