"""Narrowest copper on each power path: the largest disc that can slide through the net's copper
from the source pad until it touches the target pad (binary search on the disc diameter).

usage: python neck_width.py paths.npz      (system python with numpy + scipy)
"""
import sys
import numpy as np
from scipy import ndimage

d = np.load(sys.argv[1])
res = float(d['res'])
names = list(d['names'])
dt_cache = {}
for i, name in enumerate(names):
    c, s, t = d['c%d' % i], d['s%d' % i], d['t%d' % i]
    k = c.tobytes().__hash__()
    if k not in dt_cache:
        dt_cache[k] = ndimage.distance_transform_edt(c) * res    # mm to the nearest non-copper pixel
    dc = dt_cache[k]
    ds = ndimage.distance_transform_edt(~s) * res                 # mm to the source pad
    dtg = ndimage.distance_transform_edt(~t) * res                # mm to the target pad

    def ok(r):
        centres = dc >= r
        lab, n = ndimage.label(centres)
        if n == 0:
            return False
        a = set(np.unique(lab[centres & (ds <= r + res)])) - {0}
        b = set(np.unique(lab[centres & (dtg <= r + res)])) - {0}
        return bool(a & b)

    lo, hi = 0.0, 20.0
    if not ok(res):
        print('%-40s  NOT CONNECTED' % name)
        continue
    while hi - lo > 0.05:
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if ok(mid) else (lo, mid)
    print('%-40s  %5.1f mm' % (name, 2 * lo))
