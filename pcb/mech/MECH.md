# racebot_main: mechanical hand-off

Files in this folder:
- `racebot_main.step`: board plus components. XT60 J101 uses your supplied model. The fuse
  holder and ESP32 DevKit are envelope blocks (see "Envelopes" below).
- `racebot_main_outline.dxf`: board outline (layer `Edge.Cuts`) and the 4 mounting holes (layer
  `User.Drawings`, Ø3.2 circles). Units mm.

## Coordinate frame (same in the STEP and the DXF)

- Origin = **rear-left corner** of the PCB, bottom surface (z = 0).
- **+X** points to the right. **+Y** points to the front (the ESP32 antenna end). **+Z** points up.
- The board top surface is at z = 1.6 mm. All heights below are measured **above the board top**.

## Board

| Item | Value |
|---|---|
| Size | **108.0 × 76.0 mm**, rectangular |
| Thickness | 1.6 mm, 2 layers (order 2 oz copper) |
| ESP32 DevKit overhang | 5.6 mm past the **front** edge (y 76.0 → 81.6), centred at x = 54 |
| Below the board | THT pins stick out up to **2.9 mm**. Use **≥5 mm standoffs** |

## Mounting holes (M3, Ø3.2 mm, non-plated)

| Hole | X | Y |
|---|---|---|
| H1 rear-left | 3.5 | 3.5 |
| H2 rear-right | 104.5 | 3.5 |
| H3 front-left | 3.5 | 72.5 |
| H4 front-right | 104.5 | 72.5 |

Keep about Ø7 mm clear around each hole for screw heads and standoffs.

## Tallest parts (height above board top)

| Part | Height | Footprint area (x, y) |
|---|---|---|
| **F101 ATO fuse holder + fuse** | **~24 mm (estimate)** | x 21.2–41.6, y 11.5–18.0 |
| J102 XT60 switch (vertical) | 16.7 mm | x 34.4–50.4, y 2.0–10.1 |
| J101 XT60 battery (vertical) | 16.5 mm | x 15.7–30.8, y 2.3–9.7 |
| Motor screw terminals | 13.8 mm | see below |
| ESP32 DevKit on sockets | 13.3 mm | x 39.8–68.2, y 25.6–81.6 |
| 470 µF bulk caps (Ø10) | 12.5 mm (real part; the STEP model is 10 mm) | body centres C407 (34.2, 70.7), C408 (31.0, 52.4), C507 (77.0, 54.4), C508 (73.8, 33.4) |
| ELRS header J203 | 8.5 mm | x 60.8–72.0, y 13.4–17.0 (horizontal row) |

**The fuse height is an estimate:** holder plus a fitted ATO blade. Measure your real fuse holder and
update it. Leave **access from above** to swap the fuse.

The XT60s are **vertical**, so the mated plugs and leads go **straight up**. Allow about **45 mm
above the board** at J101/J102 for the plug, wire and bend radius, or route the leads sideways
through a slot.

## Connector exits

| Connector | Where | Direction |
|---|---|---|
| **J101 battery XT60** (male) | rear-left, centre x ≈ 23.6, y = 6 | plug from **above**. Pad at x = 20 is −, x = 27.2 is + |
| **J102 power switch / kill link XT60** (female) | rear, centre x ≈ 42.4, y = 6 | plug from **above** |
| **Left motors** J401 (front) / J402 (rear) | **left edge** x = 0; J401 pads y 65.5 / 60.4, J402 pads y 53.5 / 48.4 | wire entry faces **−X** |
| **Right motors** J501 (front) / J502 (rear) | **right edge** x = 108; same Y as the left side | wire entry faces **+X** |
| ELRS receiver lead (J203) | rear middle, pins in a row at y = 15.2: x 62.6 (5V), 65.1 (GND), 67.7 (RX), 70.2 (TX) | header pins up, plug from above |
| ESP32 DevKit USB (micro-USB) | rear end of the DevKit, x ≈ 54, y ≈ 26–30, z ≈ 10–13 | cable plugs in from the **rear (−Y)** |
| **ESP32 antenna** | front overhang, x 45–63, y 76–81.6 | keep metal and carbon away from the front and top |

Motor wiring: the **front pad of every motor terminal is OUT_A**. Wire the same motor lead (e.g. red)
to the front pad on all four motors.

## Envelopes (not real models)

- `pcb/3d/ATO_holder_with_fuse_envelope.step`: 20.4 × 6.5 × 13 mm holder plus 19.1 × 5.1 mm fuse,
  24 mm total.
- `pcb/3d/ESP32_DevKit38_on_sockets_envelope.step`: 28.3 × 55 mm DevKit on 8.5 mm sockets,
  module/shield and micro-USB as blocks.

## Regenerating

Run from the `pcb/` folder after changing the layout:

```
kicad-cli pcb export step --drill-origin --subst-models -f -o mech/racebot_main.step racebot_main.kicad_pcb
kicad-cli pcb export dxf --layers Edge.Cuts,Dwgs.User --mode-single --udo --ou mm --drill-shape-opt 0 -o mech/racebot_main_outline.dxf racebot_main.kicad_pcb
```
