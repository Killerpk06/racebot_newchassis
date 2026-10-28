"""Tiny 2-layer grid A* router: connects the unconnected islands of one net with DRC-clean tracks + vias.

usage: miniroute.py board.kicad_pcb "<net name>"
"""
import sys, heapq, math
import pcbnew

PCB, NET = sys.argv[1], sys.argv[2]
b = pcbnew.LoadBoard(PCB)
mm, tomm = pcbnew.FromMM, pcbnew.ToMM
G = 0.1                      # grid (mm)
TW = float(__import__("os").environ.get("MR_TW", "0.25"))  # track width


def clr(netname):
    """clearance to an obstacle of this net (power class 0.3 mm, 5 V class 0.25 mm, signals 0.2 mm) + margin"""
    if any(s in netname for s in ('VMOT', 'GND', 'BAT_', 'VBAT_F', '_OUT_')):
        return 0.32
    if netname in ('+5V', '+3V3') or 'SW_5V' in netname:
        return 0.27
    return 0.22


CL = 0.32
VD, VDR = 0.6, 0.3           # via
bb = b.GetBoardEdgesBoundingBox()
X0, Y0 = tomm(bb.GetX()), tomm(bb.GetY())
NX, NY = int(tomm(bb.GetWidth()) / G) + 1, int(tomm(bb.GetHeight()) / G) + 1
LAY = [pcbnew.F_Cu, pcbnew.B_Cu]
block = [bytearray(NX * NY), bytearray(NX * NY)]   # 1 = track centre not allowed
vblock = bytearray(NX * NY)                          # 1 = via centre not allowed (either layer / holes)


def mark(arr, x0, y0, x1, y1, r, test):
    i0, i1 = max(0, int((min(x0, x1) - r - X0) / G)), min(NX - 1, int((max(x0, x1) + r - X0) / G) + 1)
    j0, j1 = max(0, int((min(y0, y1) - r - Y0) / G)), min(NY - 1, int((max(y0, y1) + r - Y0) / G) + 1)
    for j in range(j0, j1 + 1):
        y = Y0 + j * G
        for i in range(i0, i1 + 1):
            if test(X0 + i * G, y, r):
                arr[j * NX + i] = 1


def seg_test(ax, ay, bx, by):
    def f(x, y, r):
        dx, dy = bx - ax, by - ay
        L = dx * dx + dy * dy
        t = 0 if L == 0 else max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / L))
        return math.hypot(x - ax - t * dx, y - ay - t * dy) <= r
    return f


def rect_test(cx, cy, hx, hy):
    def f(x, y, r):
        ex, ey = max(abs(x - cx) - hx, 0), max(abs(y - cy) - hy, 0)
        return math.hypot(ex, ey) <= r
    return f


# board edge keep-out
for L in (0, 1):
    for i in range(NX):
        for j in range(NY):
            x, y = X0 + i * G, Y0 + j * G
            if x < X0 + 0.5 or y < Y0 + 0.5 or x > X0 + tomm(bb.GetWidth()) - 0.5 or y > Y0 + tomm(bb.GetHeight()) - 0.5:
                block[L][j * NX + i] = 1
                vblock[j * NX + i] = 1

# layout v2 routing areas: F.Cu only in the logic / rear-middle areas and fan-out windows, B.Cu not in KEEP_B
import os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from layout_v2 import WINDOWS_F, KEEP_B, H as _H, OX as _OX, OY as _OY
_OKF = [(39.5, 0, 68.5, 49.6), (56.6, 59.1, 79.2, _H)] + list(WINDOWS_F)
_KB = [(min(p[0] for p in r), min(p[1] for p in r), max(p[0] for p in r), max(p[1] for p in r)) for r in KEEP_B]
for j in range(NY):
    y = Y0 + j * G - _OY
    for i in range(NX):
        x = X0 + i * G - _OX
        if not any(a + TW / 2 + 0.2 <= x <= c - TW / 2 - 0.2 and q + TW / 2 + 0.2 <= y <= d - TW / 2 - 0.2 for a, q, c, d in _OKF):
            block[0][j * NX + i] = 1
            vblock[j * NX + i] = 1
        if any(a - 0.35 <= x <= c + 0.35 and q - 0.35 <= y <= d + 0.35 for a, q, c, d in _KB):
            block[1][j * NX + i] = 1
            vblock[j * NX + i] = 1

own = []      # same-net copper: list of (layer set, test fn)
for t in b.GetTracks():
    same = t.GetNetname() == NET
    if t.Type() == pcbnew.PCB_VIA_T:
        x, y, r = tomm(t.GetPosition().x), tomm(t.GetPosition().y), tomm(t.GetWidth(pcbnew.F_Cu)) / 2
        if same:
            own.append(((0, 1), x, y))
            continue
        c = clr(t.GetNetname())
        for L in (0, 1):
            mark(block[L], x, y, x, y, r + c + TW / 2, rect_test(x, y, 0, 0))
        mark(vblock, x, y, x, y, r + c + VD / 2, rect_test(x, y, 0, 0))
    else:
        L = LAY.index(t.GetLayer())
        ax, ay, bx2, by2 = tomm(t.GetStart().x), tomm(t.GetStart().y), tomm(t.GetEnd().x), tomm(t.GetEnd().y)
        hw = tomm(t.GetWidth()) / 2
        if same:
            own.append(((L,), ax, ay))
            own.append(((L,), bx2, by2))
            continue
        c = clr(t.GetNetname())
        mark(block[L], ax, ay, bx2, by2, hw + c + TW / 2, seg_test(ax, ay, bx2, by2))
        mark(vblock, ax, ay, bx2, by2, hw + c + VD / 2, seg_test(ax, ay, bx2, by2))

pads_same = []
for f in b.GetFootprints():
    for p in f.Pads():
        bx = p.GetBoundingBox()
        cx, cy = tomm(bx.GetCenter().x), tomm(bx.GetCenter().y)
        hx, hy = tomm(bx.GetWidth()) / 2, tomm(bx.GetHeight()) / 2
        th = p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
        layers = (0, 1) if th else ((0,) if p.IsOnLayer(pcbnew.F_Cu) else (1,))
        if p.GetNetname() == NET and p.GetNetname():
            pads_same.append((layers, tomm(p.GetPosition().x), tomm(p.GetPosition().y), f.GetReference()))
            continue
        c = clr(p.GetNetname())
        for L in layers:
            mark(block[L], cx - hx, cy - hy, cx + hx, cy + hy, c + TW / 2, rect_test(cx, cy, hx, hy))
        mark(vblock, cx - hx, cy - hy, cx + hx, cy + hy, max(c, 0.3) + VD / 2, rect_test(cx, cy, hx, hy))

# connectivity islands of the net (geometric: shared end points, ends inside pads, vias join layers)
items = [t for t in b.GetTracks() if t.GetNetname() == NET]
for f in b.GetFootprints():
    items += [p for p in f.Pads() if p.GetNetname() == NET]
parent = list(range(len(items)))


def find(a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return a


def ends(it):
    """(layers, point) contact points of an item."""
    if isinstance(it, pcbnew.PAD):
        th = it.GetAttribute() == pcbnew.PAD_ATTRIB_PTH
        return [((0, 1) if th else ((0,) if it.IsOnLayer(pcbnew.F_Cu) else (1,)), it.GetPosition())]
    if it.Type() == pcbnew.PCB_VIA_T:
        return [((0, 1), it.GetPosition())]
    L = (LAY.index(it.GetLayer()),)
    return [(L, it.GetStart()), (L, it.GetEnd())]


def touches(a, b2):
    for la, pa in ends(a):
        if isinstance(b2, pcbnew.PAD):
            lb = ends(b2)[0][0]
            if set(la) & set(lb) and b2.HitTest(pa, mm(0.01)):
                return True
        if not isinstance(b2, pcbnew.PAD) and b2.Type() != pcbnew.PCB_VIA_T and set(la) & {LAY.index(b2.GetLayer())}:
            if b2.HitTest(pa, mm(0.01)):
                return True
        for lb, pb in ends(b2):
            if set(la) & set(lb) and (pa - pb).EuclideanNorm() < mm(0.02):
                return True
    return False


for x in range(len(items)):
    for y in range(x + 1, len(items)):
        if touches(items[x], items[y]) or touches(items[y], items[x]):
            parent[find(x)] = find(y)
groups = {}
for k, it in enumerate(items):
    groups.setdefault(find(k), []).append(it)
print('islands:', len(groups))
if len(groups) < 2:
    sys.exit(0)


def cells_of(it):
    """start/goal cells for an item: its pad centre or track points, on its layers."""
    out = []
    if isinstance(it, pcbnew.PAD):
        x, y = tomm(it.GetPosition().x), tomm(it.GetPosition().y)
        th = it.GetAttribute() == pcbnew.PAD_ATTRIB_PTH
        lays = (0, 1) if th else ((0,) if it.IsOnLayer(pcbnew.F_Cu) else (1,))
        pts = [(x, y)]
    elif it.Type() == pcbnew.PCB_VIA_T:
        lays = (0, 1)
        pts = [(tomm(it.GetPosition().x), tomm(it.GetPosition().y))]
    else:
        lays = (LAY.index(it.GetLayer()),)
        pts = [(tomm(it.GetStart().x), tomm(it.GetStart().y)), (tomm(it.GetEnd().x), tomm(it.GetEnd().y))]
    for x, y in pts:
        i, j = int(round((x - X0) / G)), int(round((y - Y0) / G))
        for L in lays:
            out.append((L, i, j))
    return out


gl = list(groups.values())
# connect pad-to-pad where an island has pads (track stubs may be cleaned up later)
gl = [g if __import__('os').environ.get('MR_ALL') else ([it for it in g if isinstance(it, pcbnew.PAD)] or g) for g in gl]
_rot = int(__import__('os').environ.get('MR_ROT', '0')) % len(gl)
gl = gl[_rot:] + gl[:_rot]
for _g in gl:
    print('  island:', sorted(set((it.GetParentFootprint().GetReference() + '.' + it.GetNumber()) if isinstance(it, pcbnew.PAD) else 'track' for it in _g))[:6])
src = set(c for it in gl[0] for c in cells_of(it))
dst = set(c for g in gl[1:] for it in g for c in cells_of(it))
# endpoints sit inside the pad keep-out of their own pad only, so clear a small disc around them
for (L, i, j) in list(src) + list(dst):
    for dj in range(-6, 7):
        for di in range(-6, 7):
            if 0 <= i + di < NX and 0 <= j + dj < NY and math.hypot(di, dj) <= 2:
                block[L][(j + dj) * NX + i + di] = 0

VIA_COST = 40
pq, came, cost = [], {}, {}
for s in src:
    cost[s] = 0
    heapq.heappush(pq, (0, s))
goal = None
tx = [c for c in dst]
while pq:
    c, cur = heapq.heappop(pq)
    if cur in dst:
        goal = cur
        break
    if c > cost.get(cur, 1e18):
        continue
    L, i, j = cur
    for di, dj, w in ((1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)):
        ni, nj = i + di, j + dj
        if not (0 <= ni < NX and 0 <= nj < NY) or block[L][nj * NX + ni]:
            continue
        n = (L, ni, nj)
        nc = c + w
        if nc < cost.get(n, 1e18):
            cost[n], came[n] = nc, cur
            heapq.heappush(pq, (nc, n))
    if not vblock[j * NX + i] and not block[1 - L][j * NX + i]:
        n = (1 - L, i, j)
        nc = c + VIA_COST
        if nc < cost.get(n, 1e18):
            cost[n], came[n] = nc, cur
            heapq.heappush(pq, (nc, n))
if goal is None:
    print('NO PATH')
    sys.exit(1)
path = [goal]
while path[-1] in came:
    path.append(came[path[-1]])
path.reverse()
netinfo = b.GetNetsByName()[NET]


def P(i, j):
    return pcbnew.VECTOR2I(mm(X0 + i * G), mm(Y0 + j * G))


# compress into straight runs
segs, vias = [], []
run = [path[0]]
for a, c2 in zip(path, path[1:]):
    if a[0] != c2[0]:
        vias.append((a[1], a[2]))
        segs.append(run)
        run = [c2]
        continue
    if len(run) >= 2:
        d1 = (run[-1][1] - run[-2][1], run[-1][2] - run[-2][2])
        d2 = (c2[1] - a[1], c2[2] - a[2])
        if d1 != d2:
            segs.append(run)
            run = [a]
    run.append(c2)
segs.append(run)
n = 0
for r in segs:
    if len(r) < 2:
        continue
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(P(r[0][1], r[0][2]))
    t.SetEnd(P(r[-1][1], r[-1][2]))
    t.SetWidth(mm(TW))
    t.SetLayer(LAY[r[0][0]])
    t.SetNet(netinfo)
    b.Add(t)
    n += 1
for i, j in vias:
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(P(i, j))
    v.SetWidth(mm(VD))
    v.SetDrill(mm(VDR))
    v.SetNet(netinfo)
    b.Add(v)
b.Save(PCB)
print('routed: %d segments, %d vias, length %.1f mm' % (n, len(vias), cost[goal] * G))
