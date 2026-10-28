"""racebot_main layout v2: placement, pours, fixed copper and routing keep-outs (shared by the
rework_place / rework_finish scripts).

Board coordinates in mm: origin = board top-left corner (pcbnew 100,100), +x right, +y toward the
rear edge (XT60s). Left bridge = U401/U402, right bridge = U501/U502.

Power is carried by pours only (no power tracks): F.Cu VMOT is the lowest-priority fill and gets
everything the other F.Cu pours leave. B.Cu is the GND plane.
"""
import re
import pcbnew

OX, OY = 100.0, 100.0
W, H = 108.0, 76.0
mm = pcbnew.FromMM


def P(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


def bxy(v):
    return (pcbnew.ToMM(v.x) - OX, pcbnew.ToMM(v.y) - OY)


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


# ------------------------------------------------------------------ placement (x, y, rotation deg)
PLACE = {
    # left bridge: BTS tab toward the terminals, pins toward the DevKit, VS (pin 7) at the top of each row
    'U401': (19.0, 13.0, 180), 'U402': (19.0, 34.2, 180),
    'J401': (5.4, 10.5, 270), 'J402': (5.4, 22.5, 270),
    'C402': (25.5, 5.6, 90), 'C403': (27.6, 5.8, 90),          # U401 VS ceramics, above pin 7
    'C407': (31.7, 5.3, 0),                                    # U401 bulk: VS corner, GND pad at the dead end
    'C408': (33.5, 23.6, 180),                                 # U402 bulk: GND pad in the U401 pin-1 island
    'C405': (25.0, 26.84, 90), 'C406': (23.2, 27.06, 90),      # U402 VS ceramics, GND pads in the same island
    # right bridge (BTS rotated, not mirrored: VS at the bottom of each row)
    'U501': (89.0, 11.0, 0), 'U502': (89.0, 32.2, 0),
    'J501': (102.6, 15.58, 90), 'J502': (102.6, 27.58, 90),
    'C502': (83.0, 18.36, 270), 'C503': (84.75, 18.14, 270),   # U501 VS ceramics, GND pads in the U502 pin-1 island
    'C507': (74.5, 21.6, 0),                                   # U501 bulk: GND pad in the U502 pin-1 island
    'C505': (82.5, 39.56, 270), 'C506': (80.4, 39.34, 270),    # U502 VS ceramics, below pin 7
    'C508': (76.3, 42.6, 180),                                 # U502 bulk, below pin 7
    # under the DevKit (<= 8.5 mm): column A = left-bridge resistors, F = right-bridge resistors
    'R404': (45.2, 9.0, 0), 'R403': (45.2, 11.0, 0), 'R402': (45.2, 13.0, 0), 'R401': (45.2, 15.0, 0),
    'R104': (48.6, 17.6, 0), 'C105': (51.8, 17.6, 0),
    'R301': (45.2, 22.32, 0), 'R302': (45.2, 24.86, 0), 'R303': (45.2, 27.4, 0),
    'R409': (45.2, 31.0, 0), 'R408': (45.2, 33.0, 0), 'R407': (45.2, 35.0, 0), 'R406': (45.2, 37.0, 0),
    # IS filters (1k + 10n + BAT54S) next to the ADC pins J201.3..6
    'R505': (48.6, 3.0, 0), 'C501': (51.8, 3.0, 0), 'D501': (55.4, 3.0, 0),
    'R510': (48.6, 6.6, 0), 'C504': (51.8, 6.6, 0), 'D502': (55.4, 6.6, 0),
    'R405': (48.6, 10.2, 0), 'C401': (51.8, 10.2, 0), 'D401': (55.4, 10.2, 0),
    'R410': (48.6, 13.8, 0), 'C404': (51.8, 13.8, 0), 'D402': (55.4, 13.8, 0),
    'U301': (54.0, 30.0, 0), 'C301': (61.0, 25.4, 90),
    'R306': (62.9, 4.54, 0),
    'R501': (62.9, 7.4, 0), 'R502': (62.9, 9.4, 0), 'R503': (62.9, 11.4, 0), 'R504': (62.9, 13.4, 0),
    'R305': (62.9, 19.78, 0), 'R304': (62.9, 22.32, 0),
    'R506': (62.9, 29.7, 0), 'R507': (62.9, 31.7, 0), 'R508': (62.9, 33.7, 0), 'R509': (62.9, 35.7, 0),
    'J201': (41.3, 2.0, 0), 'J202': (66.7, 2.0, 0),
    'R103': (44.0, 49.6, 90),                                  # VBAT divider top: VMOT pad on the bus
    # power entry (positions fixed by the mech hand-off)
    'J101': (20.0, 70.0, 0), 'F101': (25.0, 60.0, 0), 'J102': (46.0, 70.0, 180),
    'Q101': (12.0, 69.6, 270),                                  # source pins up, drain pad toward J101
    'R101': (6.0, 58.4, 270), 'R102': (4.3, 61.5, 180), 'D101': (3.6, 64.5, 180),
    'D102': (55.5, 63.0, 0),
    # rear middle: ELRS header + LEDs (visible, clear of the DevKit and the buck)
    'J203': (62.6, 60.8, 90),        # horizontal along the bus edge: keeps the B.Cu return strip wide
    'R201': (70.6, 63.9, 0), 'D201': (70.6, 66.5, 0),
    'R105': (73.8, 63.9, 0), 'D104': (73.8, 66.5, 0),
    'R106': (77.0, 58.9, 270), 'D105': (77.0, 66.5, 0),
    # 5 V buck, rear-right: pins face the front, tab toward the rear edge
    'U101': (88.0, 68.8, 270), 'D103': (87.7, 56.5, 180), 'L101': (85.8, 47.9, 90),
    'C102': (94.4, 64.4, 270), 'C103': (94.45, 44.5, 0), 'C104': (94.6, 49.4, 270),
}
C101_CENTER = (96.6, 55.0)       # body centre; pads are aimed at U101 pin 1 (computed in place_c101)


def place_c101(board):
    """C101 (radial, origin = pad 1): put the body at C101_CENTER with pad 1 (VMOT) aimed at U101 pin 1."""
    import math
    u = board.FindFootprintByReference('U101')
    p1 = [p for p in u.Pads() if p.GetNumber() == '1' and p.GetSize().x < mm(5)][0]
    tx, ty = bxy(p1.GetPosition())
    cx, cy = C101_CENTER
    dx, dy = tx - cx, ty - cy
    n = math.hypot(dx, dy)
    ux, uy = dx / n, dy / n
    x1, y1 = cx + 1.75 * ux, cy + 1.75 * uy        # pad 1 (VMOT)
    # pad 2 sits at +3.5 along the footprint x axis; it must point away from pin 1
    ang = math.degrees(math.atan2(uy, -ux))         # KiCad rotation is CCW on screen (y down)
    f = board.FindFootprintByReference('C101')
    f.SetOrientationDegrees(ang)
    f.SetPosition(P(x1, y1))


# ------------------------------------------------------------------ BTS fan-out (signal pins 2,3,5,6)
FANOUT_X = {'U401': 23.3, 'U402': 23.3, 'U501': 84.7, 'U502': 84.7}   # via column under the package body
STUB_FROM = {'U401': 24.8, 'U402': 24.8, 'U501': 83.2, 'U502': 83.2}

# ------------------------------------------------------------------ pours
# (name, net, layer, priority, polygon)
E = 0.5
L_OUT_A, L_OUT_B = '/Motor Bridge L/L_OUT_A', '/Motor Bridge L/L_OUT_B'
R_OUT_A, R_OUT_B = '/Motor Bridge R/R_OUT_A', '/Motor Bridge R/R_OUT_B'
ZONES = [
    ('GND_bottom', 'GND', 'B', 0, rect(0.3, 0.3, W - 0.3, H - 0.3)),
    ('VMOT_top', 'VMOT', 'F', 0, rect(0.3, 0.3, W - 0.3, H - 0.3)),
    ('GND_logic', 'GND', 'F', 1, rect(39.7, 0.3, 68.3, 49.4)),
    # ---- left bridge
    ('L_OUT_A_top', L_OUT_A, 'F', 2, [(E, E), (22.5, E), (22.5, 18.4), (12.5, 18.4), (12.5, 13.98), (E, 13.98)]),
    ('L_OUT_B_top', L_OUT_B, 'F', 2, [(E, 14.28), (12.2, 14.28), (12.2, 28.5), (22.5, 28.5), (22.5, 39.6), (E, 39.6)]),
    ('L_OUT_A_bottom', L_OUT_A, 'B', 2, rect(E, 8.0, 12.0, 25.0)),
    ('U401_GND', 'GND', 'F', 3, [(12.8, 18.7), (22.5, 18.7), (22.5, 16.3), (29.5, 16.3), (29.5, 22.0), (30.1, 22.0),
                                  (30.1, 25.2), (26.1, 25.2), (26.1, 26.95), (22.5, 26.95), (22.5, 28.2), (12.8, 28.2)]),
    ('U402_GND', 'GND', 'F', 3, [(12.8, 39.9), (22.5, 39.9), (22.5, 37.5), (29.5, 37.5), (29.5, 44.0), (12.8, 44.0)]),
    ('C402_GND', 'GND', 'F', 3, rect(22.8, E, 28.6, 5.7)),
    # ---- right bridge
    ('R_OUT_A_top', R_OUT_A, 'F', 2, [(85.5, 5.6), (W - E, 5.6), (W - E, 13.98), (96.0, 13.98), (96.0, 16.4), (85.5, 16.4)]),
    ('R_OUT_B_top', R_OUT_B, 'F', 2, [(96.3, 14.28), (W - E, 14.28), (W - E, 37.9), (85.5, 37.9), (85.5, 26.8), (96.3, 26.8)]),
    ('R_OUT_A_bottom', R_OUT_A, 'B', 2, rect(96.3, 8.0, W - E, 25.0)),
    ('U501_GND', 'GND', 'F', 3, [(68.8, E), (101.2, E), (101.2, 5.3), (85.55, 5.3), (85.55, 7.7), (78.75, 7.7),
                                  (78.75, 11.5), (68.8, 11.5)]),
    ('U502_GND', 'GND', 'F', 3, [(78.1, 20.3), (81.6, 20.3), (81.6, 18.25), (85.55, 18.25), (85.55, 16.7), (96.0, 16.7),
                                  (96.0, 26.5), (85.5, 26.5), (85.5, 28.9), (78.1, 28.9)]),
    ('C505_GND', 'GND', 'F', 3, [(79.2, 39.45), (84.2, 39.45), (84.2, 41.1), (82.4, 41.1), (82.4, 42.8), (79.2, 42.8)]),
    # ---- power entry
    ('Q101_source_GND', 'GND', 'F', 3, [(6.6, 57.4), (23.4, 57.4), (23.4, 66.6), (14.6, 66.6), (14.6, 67.2),
                                         (10.65, 67.2), (10.65, 66.25), (6.6, 66.25)]),
    ('Q101_gate_GND', 'GND', 'F', 3, [(E, 60.3), (5.5, 60.3), (5.5, 67.2), (9.0, 67.2), (9.0, H - E), (E, H - E)]),
    ('BAT_NEG', '/Power/BAT_NEG', 'F', 2, [(9.3, 67.5), (14.6, 67.5), (14.6, 66.9), (23.5, 66.9), (23.5, H - E), (9.3, H - E)]),
    ('BAT_POS', '/Power/BAT_POS', 'F', 2, rect(23.8, 58.3, 30.7, H - E)),
    ('VBAT_F', '/Power/VBAT_F', 'F', 2, rect(32.3, 58.3, 41.9, H - E)),
    # ---- rear: ELRS/LED area + buck ground (one polygon), buck SW node and 5 V output
    ('GND_rear', 'GND', 'F', 2, [(56.8, 59.1), (79.3, 59.1), (79.3, 55.0), (90.6, 55.0), (90.6, 64.4),
                                  (W - E, 64.4), (W - E, H - E), (56.8, H - E)]),
    ('SW_5V', '/Power/SW_5V', 'F', 4, [(82.8, 51.0), (91.2, 51.0), (91.2, 57.7), (90.5, 57.7), (90.5, 59.3),
                                        (88.9, 59.3), (88.9, 57.75), (87.3, 57.75), (87.3, 54.9), (82.8, 54.9)]),
    ('+5V_buck', '+5V', 'F', 4, rect(82.8, 41.4, 95.6, 46.4)),
]

# ------------------------------------------------------------------ fixed vias: (x, y, net, pad, drill)
V_PWR = (1.0, 0.6)       # power-ground vias (task spec: 0.6 mm drill / 1.0 mm pad)
FIXED_VIAS = []


def _vias(net, pts, size=V_PWR):
    FIXED_VIAS.extend((x, y, net, size[0], size[1]) for x, y in pts)


# BTS pin-1 islands: 12 vias each
_vias('GND', [(24.6, 18.2), (26.4, 18.2), (28.2, 18.2)] + [(x, 20.4) for x in (16.0, 18.4, 20.8, 23.2, 25.6, 28.0)]
      + [(x, 22.8) for x in (16.0, 18.4, 20.8)])                                                      # U401
_vias('GND', [(24.6, 39.2), (26.4, 39.2), (28.2, 39.2)] + [(x, 41.2) for x in (15.0, 17.5, 20.0, 22.5, 25.0, 27.5)]
      + [(x, 43.0) for x in (15.0, 17.5, 20.0)])                                                      # U402
_vias('GND', [(79.8, 6.0), (81.6, 6.0), (83.4, 6.0)] + [(x, 3.6) for x in (79.0, 81.0, 83.0, 85.0, 87.5, 90.0, 92.5)]
      + [(87.5, 1.6), (90.0, 1.6)])                                                                   # U501
_vias('GND', [(79.8, 27.0), (81.6, 27.0), (83.4, 27.0)] + [(x, 24.6) for x in (80.0, 82.0, 84.0, 86.5, 89.0, 91.5, 94.0)]
      + [(86.5, 22.2), (89.0, 22.2)])                                                                 # U502
# Q101 source island: 17 vias
_vias('GND', [(x, y) for y in (59.0, 61.4, 63.8) for x in (9.0, 12.0, 15.0, 18.0, 21.0)] + [(11.4, 65.6), (13.2, 65.6)])
_vias('GND', [(1.8, 61.5), (3.5, 66.8), (1.5, 68.6)])                       # gate-network GND patch
_vias('GND', [(24.0, 2.0), (25.8, 2.0), (27.6, 2.0)])                       # C402/C403 ground
_vias('GND', [(80.0, 42.1), (81.6, 42.1)])                                  # C505/C506 ground
_vias('GND', [(59.0, 60.7), (59.0, 65.3), (61.5, 63.8), (61.5, 65.4)])      # D102 TVS ground
_vias('GND', [(80.4, y) for y in (60.0, 63.0, 66.0, 69.0, 72.0, 74.6)] + [(95.8, y) for y in (67.0, 70.0, 73.0)]
      + [(83.3, 56.2), (83.3, 57.8)])                                       # buck ground / D103 anode
_vias('GND', [(94.6, 51.5)], (0.8, 0.4))                                    # C104 ground

POWER_NETS = ['GND', 'VMOT', '/Power/BAT_NEG', '/Power/BAT_POS', '/Power/VBAT_F', '/Power/SW_5V',
              '/Power/Q_GATE', L_OUT_A, L_OUT_B, R_OUT_A, R_OUT_B]

# ------------------------------------------------------------------ hand-routed copper: (x0, y0, x1, y1, width, layer, net)
FIXED_TRACKS = [
    # Q101 gate network spine
    (6.0, 59.225, 6.0, 66.7, 0.3, 'F', '/Power/Q_GATE'), (6.0, 66.7, 10.095, 66.7, 0.3, 'F', '/Power/Q_GATE'),
    (5.125, 61.5, 6.0, 61.5, 0.3, 'F', '/Power/Q_GATE'), (5.25, 64.5, 6.0, 64.5, 0.3, 'F', '/Power/Q_GATE'),
    # buck output: FB (pin 4) -> via -> B.Cu -> via -> L101 pad 2; C103/C104 to L101 pad 2
    (86.3, 60.0, 86.3, 58.3, 0.5, 'F', '+5V'), (86.3, 58.3, 86.3, 48.0, 0.5, 'B', '+5V'),
    (86.3, 48.0, 84.0, 46.0, 0.5, 'B', '+5V'), (84.0, 46.0, 85.8, 43.05, 0.5, 'F', '+5V'),
    (94.45, 44.5, 85.8, 43.05, 0.5, 'F', '+5V'), (94.6, 48.625, 94.45, 44.5, 0.5, 'F', '+5V'),
    (94.6, 50.175, 94.6, 51.5, 0.4, 'F', 'GND'),
]
FIXED_SIGNAL_VIAS = [(86.3, 58.3, '+5V', 0.8, 0.4), (84.0, 46.0, '+5V', 0.8, 0.4)]

# ------------------------------------------------------------------ routing keep-outs (rule areas, removed after routing)
KEEP_F_RAW = [(0, 0, 39.5, H), (68.5, 0, W, 59.1), (39.5, 49.6, 68.5, 59.1),
              (39.5, 59.1, 56.6, H), (79.2, 59.1, W, H)]
# windows in the F.Cu keep-out where the router reaches pre-placed copper (fan-out vias, buck 5 V via)
WINDOWS_F = [(22.4, 9.5, 29.5, 16.5), (22.4, 30.7, 29.5, 37.7),       # U401, U402 pins 2..6
             (78.5, 7.5, 85.5, 14.5), (78.5, 28.7, 85.5, 35.7),       # U501, U502 pins 2..6
             (83.3, 45.3, 84.7, 46.7)]                                # buck +5V via


def _subtract(r, wins):
    """Split rectangle r minus the window rectangles into row strips of rectangles."""
    x0, y0, x1, y1 = r
    ws = [(max(a, x0), max(b, y0), min(c, x1), min(d, y1)) for a, b, c, d in wins if a < x1 and c > x0 and b < y1 and d > y0]
    ys = sorted(set([y0, y1] + [w[1] for w in ws] + [w[3] for w in ws]))
    out = []
    for ya, yb in zip(ys, ys[1:]):
        cut = sorted((w[0], w[2]) for w in ws if w[1] <= ya and w[3] >= yb)
        x = x0
        for a, c in cut:
            if a > x:
                out.append(rect(x, ya, a, yb))
            x = max(x, c)
        if x < x1:
            out.append(rect(x, ya, x1, yb))
    return out


KEEP_F = [q for r in KEEP_F_RAW for q in _subtract(r, WINDOWS_F)]
KEEP_B = [rect(0, 0, 22.4, H), rect(85.6, 0, W, 38.0),
          rect(22.9, 16.4, 30.5, 29.4), rect(22.9, 37.6, 30.5, 44.5),          # left pin-1 islands / gap
          rect(68.8, 0, 85.1, 7.6), rect(77.8, 14.4, 85.1, 28.8),             # right pin-1 islands / gap
          rect(0, 44.0, 39.6, H), rect(39.6, 49.6, 58.0, H),                  # rear-left return path
          rect(87.0, 38.0, W, H), rect(79.3, 47.2, 85.6, H), rect(85.6, 59.0, 87.0, H),
          rect(58.0, 66.0, 79.3, H)]                                          # rear return strip

STACKUP = '''		(stackup
			(layer "F.SilkS" (type "Top Silk Screen"))
			(layer "F.Paste" (type "Top Solder Paste"))
			(layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
			(layer "F.Cu" (type "copper") (thickness 0.07))
			(layer "dielectric 1" (type "core") (thickness 1.44) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
			(layer "B.Cu" (type "copper") (thickness 0.07))
			(layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
			(layer "B.Paste" (type "Bottom Solder Paste"))
			(layer "B.SilkS" (type "Bottom Silk Screen"))
			(copper_finish "HAL lead-free")
			(dielectric_constraints no)
		)
'''


def write_stackup(path):
    """2-layer, 2 oz (70 um) outer copper, 1.6 mm total. Replaces any existing stackup block."""
    s = open(path, encoding='utf8').read()
    s = re.sub(r'\t\t\(stackup\n.*?\n\t\t\)\n', '', s, flags=re.S)
    s = s.replace('\t(setup\n', '\t(setup\n' + STACKUP, 1)
    open(path, 'w', encoding='utf8').write(s)


def set_netclasses(pro):
    """Net classes in the .kicad_pro (a board save from Python resets them, so call after every save)."""
    import json, copy
    d = json.load(open(pro))
    ns = d['net_settings']
    base = [c for c in ns['classes'] if c['name'] == 'Default'][0]
    base['track_width'] = 0.25

    def cls(name, tw, cl, vd, vdr, prio):
        c = copy.deepcopy(base)
        c.update(name=name, track_width=tw, clearance=cl, via_diameter=vd, via_drill=vdr, priority=prio)
        return c
    ns['classes'] = [base, cls('Power', 0.8, 0.2, 1.0, 0.6, 0), cls('Supply5V', 0.5, 0.25, 0.8, 0.4, 1)]
    pats = [('Power', p) for p in ['VMOT', 'GND', '*BAT_NEG', '*BAT_POS', '*VBAT_F', '*_OUT_A', '*_OUT_B', '*SW_5V']] + \
           [('Supply5V', p) for p in ['+5V', '+3V3']]
    ns['netclass_patterns'] = [{'netclass': c, 'pattern': p} for c, p in pats]
    json.dump(d, open(pro, 'w'), indent=2)


def layer_id(c):
    return pcbnew.F_Cu if c == 'F' else pcbnew.B_Cu
