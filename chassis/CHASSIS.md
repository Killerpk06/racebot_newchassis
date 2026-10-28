# racebot chassis v1 (wheels TBD)

Roboracer limits: 200 × 200 × 150 mm envelope, 1.5 kg (team target 1.6 kg incl. 100 g tolerance),
wireless RC only.

## Files

| File | What |
|---|---|
| `racebot_chassis.SLDASM` | Full assembly: deck, 4 MS L-clamps, 4 Johnson motors, 4 M3×10 standoffs, PCB, battery envelope |
| `racebot_deck.SLDPRT` | 2 mm 6061 deck plate (59.0 g from SolidWorks mass properties) |
| `racebot_deck_2mm_6061.dxf` | Laser/waterjet cut file for the deck, 1:1 mm, layer `CUT` |
| `racebot_chassis.step` | Neutral export of the assembly |
| `parts/` | Johnson motor, L-clamp, M3×10 spacer, PCB, battery envelope |
| `tools/deck_dxf.py` | Regenerates the DXF from the same numbers |

## Frame used in this doc

- Origin = centre of the deck, on its **bottom** face.
- +X points right, **+Y points forward**, +Z points up.
- In the SolidWorks model the same frame is mapped as: model X = −robot Y, model Y = robot X.

## Layout

| Item | Position (robot frame) |
|---|---|
| Deck | 114 × 150 × 2 mm, X ±57, Y ±75, R4 corners |
| Motors | **Hang under the deck** on MS L-clamps. The clamp face sits flush with the deck side edge (x = ±57), and the shaft points outward |
| Axles, left (x −57) | y = **+55** (front), **−27** (rear) |
| Axles, right (x +57) | y = **+27** (front), **−55** (rear) |
| Motor axis | 20.2 mm below the deck bottom |
| Battery 3S 2200 (≈106 × 35 × 25) | Lies across the front, centre (0, +34) |
| PCB 108 × 76 | Rear, centre (0, −30), on 4 × M3×10 standoffs (PCB underside 10 mm above the deck). Rotated 180°: XT60s face the battery, ESP32 antenna faces the rear |

**Why the motors are staggered.** Each motor plus clamp is 69.5 mm long, so a left and a right motor
on the same axle line can't fit in a 114 mm deck. Offsetting the left and right axles by 28 mm lets
the motor cans pass each other with about 5 mm of clearance. The layout looks the same after a 180°
turn, so the motor masses balance about the centre.

**Centre of gravity.** Battery 185 g at y = +34 against PCB + ESP32 + RX + wiring (about 195 g) at
y = −30. The CG lands within about 0.3 mm of the deck centre. The motors, clamps and wheels are
balanced by the stagger symmetry. To trim the balance, slide the battery forward or back before
tightening the straps. The strap slots allow ±3 mm.

## Deck features

- **Clamp holes:** Ø3.2, 6 per clamp (2 rows 29.8 mm apart, 5.2 / 11.2 / 17.2 mm in from the side
  edge). These match the MS L-clamp foot.
  - Use **M3 countersunk screws from the top**. The heads sit under the battery and PCB.
  - Put nyloc nuts on the clamp side.
- **PCB standoff holes:** Ø2.5, **tap M3** at (±50.5, −64.5) and (±50.5, +4.5).
  - Screw the standoff's male stud into the tapped deck. **Trim the stud to 2 mm** so it doesn't
    poke out underneath.
  - At (+50.5, −64.5) an untrimmed stud hits the right-rear clamp foot and gearbox. That's the only
    interference SolidWorks found, apart from model contact details.
- **Battery strap slots:** 4 × 22 × 3.5 mm (R1.7 ends) at (±25, +12.75) and (±25, +55.25), for two
  20 mm straps wrapping around the battery's short side.
  - Under the deck, each strap passes over the motor cans, which are 8.75 mm below the deck. It
    never passes over a gearbox, which sits only 1.85 mm below.
- **Lightening pockets:**
  - Two pockets under the PCB. Motor wires come up through these to the PCB terminals.
  - Two under the battery.
  - One at the front.
  - The pockets bring the plate from 92 g to 59 g.

## Envelope (wheels assumed Ø80 × 38 mm until chosen)

| | Value |
|---|---|
| Width at the shaft tips | 193.2 mm |
| Width with 38 mm wheels | ≈194 mm |
| Length with Ø80 wheels | (55 + 40) × 2 = **190 mm** |
| Height | deck bottom = axle + 20.2; top of fuse ≈ deck + 37.6. ≈98 mm with Ø80 wheels |
| Ground clearance | Lowest point is the clamp bottom edge, 19.8 mm below the axle: **≈20 mm** with Ø80 wheels |

**If you pick a different wheel diameter D,** move the axles so that same-side wheel centres are at
least D + 2 mm apart. Keep the 28 mm left/right stagger, and keep the total length (axle spread +
28 + D) within 200 mm.

## Mass budget (target 1,600 g)

| Item | g |
|---|---|
| Deck 2 mm 6061 | 59 |
| 4 × MS L-clamp | 79 |
| 4 × Johnson motor | 720 |
| Battery 3S 2200 | 185 |
| PCB + ESP32 + parts | 150 |
| 4 × brass standoff + clamp screws/nuts | 32 |
| RX + motor/power wiring | 45 |
| **Subtotal (no wheels)** | **1,270** |
| 4 × wheel + hex hub, at 68 g + 10 g | 312 → **1,582** |

That leaves 18 g of margin with the 68 g crawler wheels. Lighter wheels add margin one for one.

## Wiring notes

- **The PCB is mounted rotated 180°, so its "L" bridge terminals (J401/J402) end up on the robot's
  RIGHT side.** Either:
  - wire the right motors to J401/J402 and the left motors to J501/J502, then swap L/R in firmware;
  - or simply treat the board's L bridge as the right side.
- Front motor leads run under the deck, back to the PCB pockets, and up to the terminals.
- On every terminal, OUT_A is the pad toward the board's ESP32/antenna end. With the board rotated,
  that is the robot's **rear-most** pad of each terminal. Wire the same motor lead (e.g. red) to it
  on all motors on a side.
