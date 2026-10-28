import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
from layout_v2 import *
b = pcbnew.LoadBoard(sys.argv[1])
for r in ('J203', 'R201', 'D201', 'R105', 'D104', 'D105'):
    x, y, a = PLACE[r]; f = b.FindFootprintByReference(r); f.SetOrientationDegrees(a); f.SetPosition(P(x, y))
rip = {'/MCU+RX/CRSF_RX', '/MCU+RX/CRSF_TX', '/MCU+RX/STATUS_LED', '/MCU+RX/STAT_A', '/Power/LED5_A', '/Power/LEDV_A', '+5V'}
n = 0
for t in list(b.GetTracks()):
    x, y = bxy(t.GetPosition()) if t.Type() == pcbnew.PCB_VIA_T else (0, 0)
    if (not t.IsLocked() and t.GetNetname() in rip) or \
       (t.Type() == pcbnew.PCB_VIA_T and not t.IsLocked() and t.GetNetname() == 'GND' and 56.8 < x < 79.3 and 59 < y < 76):
        b.Delete(t); n += 1
b.Save(sys.argv[1]); print('moved, ripped', n)
