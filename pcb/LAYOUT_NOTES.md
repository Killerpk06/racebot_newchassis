# racebot_main: layout notes

2-layer board, 108 × 76 mm. ESP32 DevKit (38-pin) + ELRS (CRSF) + 2 full H-bridges (4× BTS7960B),
3S LiPo. Signals were autorouted with Freerouting. Power is carried by copper pours (section 1).
**Review the power copper in KiCad before ordering.**

## 1. Copper weight and high-current paths

High-current nets: `BAT_POS`, `VBAT_F`, `VMOT`, `BAT_NEG`, `GND` (return), `L_OUT_A/B`, `R_OUT_A/B`.

Required external-layer width per IPC-2221 (single layer, 25 °C ambient):

| Current | Temp rise | 1 oz (35 µm) | 2 oz (70 µm) |
|---|---|---|---|
| 20 A | +20 °C | 12.3 mm | 6.1 mm |
| 20 A | +10 °C | 18.7 mm | 9.4 mm |
| 30 A | +20 °C | 21.5 mm | 10.7 mm |
| 30 A | +10 °C | 32.7 mm | 16.4 mm |

**Order 2 oz copper.** On a board this small, 1 oz cannot carry 20–30 A in the space available.

Pour plan (zones are in the board file, priority in brackets):

| Layer | Zone | Net | Purpose |
|---|---|---|---|
| B.Cu | whole board [0] | GND | return plane |
| F.Cu | whole board [0] | VMOT | supply to both bridges, buck, TVS |
| F.Cu | under ESP32/logic [1] | GND | quiet logic ground island, stitched to B.Cu |
| F.Cu | per half-bridge [2] | x_OUT_A / x_OUT_B | BTS tab → motor terminals |
| B.Cu | terminal strip [2] | x_OUT_A | joins the two OUT_A terminal pads under the OUT_B pour |
| F.Cu | rear edge [2] | BAT_NEG / BAT_POS / VBAT_F | XT60 → Q101 / fuse / switch |
| F.Cu | at each BTS pin 1 and Q101 source [3] | GND | ground pad + vias into B.Cu |

Notes:
- Power nets have **no tracks**: pours only (plus the BTS pin-4 → tab links). Only signals were
  routed, and they are kept off F.Cu inside the power areas. Refill zones (`B`) after any edit.
- Wherever 20–30 A changes layer, use **at least 12–16 vias** (1.0 / 0.6 mm). A single via
  carries about 1.5–2 A. This applies at the XT60, fuse and switch pins, the bulk caps, every
  motor terminal and the BTS GND pads. THT pads (XT60, fuse, terminals, bulk caps) already join
  both layers.
- Power pours use solid pad connections (no thermal reliefs). Hand-soldering the XT60s needs a
  hot iron, 80 W+.
- The 20 A figures are **stall** current. Continuous current is much lower, but stall still
  heats the fuse and copper.

## 2. BTS7960B thermal copper

- **The BTS7960B tab (pin 8) is OUT, not GND.** The copper under each tab is that half-bridge's
  `x_OUT_A/B` pour. A GND or VMOT pour must never touch it.
- The BTS chips are placed tab-toward-the-terminals. The OUT pour is therefore both the heatsink
  copper and the motor-current path.
- Pin 4 (OUT) is tied to the tab by a short locked 0.8 mm track under the package.
- Add thermal vias in each tab pad: 0.3 mm drill, about 1.2 mm pitch, 20–30 vias, tented or
  plugged on the bottom. They aren't placed yet because the bottom under the tabs is GND. If
  you add them, give each tab a matching B.Cu OUT pour of the same size.
- Optional: a bottom heatsink must be electrically isolated, because the tab is at motor voltage.

## 3. Power layout (v2) and decoupling

- **Stackup:** 2 layers, **2 oz (70 µm) outer copper**, 1.6 mm (set in the board stackup, so it is
  in the Gerber job file).
- **VMOT** is the lowest-priority F.Cu pour: J102 → bus under the DevKit's rear end → a 9–10 mm
  corridor on each side, between the BTS pins and the ESP32 sockets. No VMOT tracks or vias.
- **BTS signal pins (2, 3, 5, 6)** drop to B.Cu through vias under the package body, so nothing
  crosses the VMOT corridor on F.Cu. All bridge resistors (IN/INH 10k, SR, IS load) sit under the
  DevKit.
- **BTS GND (pin 1):** F.Cu GND island per chip, 12 vias 0.6/1.0 mm into the B.Cu plane.
- **470 nF + 100 nF at each VS pin**, GND side in the neighbouring pin-1 island (or a small GND
  patch with vias).
- **Bulk 470 µF:** C408 and C507 have their GND pad inside a pin-1 island, VMOT pad in the corridor
  next to the next VS pin. C407 sits at the top of the left corridor next to U401 VS; C508 below
  U502 VS.
- **Q101 source:** F.Cu GND island with 17 vias 0.6/1.0 mm.
- **74HCT244 100 nF (C301):** next to VCC pin 20. IS filters (1 kΩ + 10 nF + BAT54S) at J201.3–6.
- `neck_report.txt` lists the narrowest copper on every power path (largest disc that slides from
  source pad to target pad). Regenerate: `tools/neck_raster.py` (KiCad python) then
  `tools/neck_width.py` (python with scipy).

## 4. LM2596 buck

- Rear-right, pins toward the front, GND tab toward the rear edge.
- C102 (100 nF) ≈2 mm from VIN pin 1 and ≈0.5 mm from the tab. C101 (220 µF) VMOT pad ≈3.5 mm from
  VIN (the courtyards of the two parts don't allow closer).
- D103 cathode 1.5 mm from pin 2 on the SW pour; anode on the GND copper joining pins 3/5 (tab
  inside the part) with vias. L101 directly beside D103. SW node is one short pour.
- FB (pin 4) drops to B.Cu at the pin and runs to the +5 V pour at L101/C103.
- ELRS header J203 is about 18 mm from the buck, on the other side of the VMOT bus.

## 5. Grounding: motor return vs logic ground

There is one GND net. Separation is done with copper geometry:
- Motor return current runs bulk-cap GND → B.Cu plane → Q101 source → XT60 −. It stays in the
  outer columns and the rear strip.
- Logic ground is the F.Cu GND island under the DevKit: header GND pins, 74HCT244, IS filters,
  VBAT divider. Stitching vias tie it to the B.Cu plane right there, under the logic.
- Don't route logic signals (INA/INB/EN, IS, CRSF) under the BTS tabs or the bulk caps.

## 6. RF: ESP32 antenna and ELRS

- The DevKit overhangs the front edge by about 5.6 mm, so the antenna has no copper under it.
  Keep the chassis free of metal and carbon in front of and above it.
- The ELRS header J203 is at the rear middle, horizontal. Route the receiver lead
  and antenna away from the motor wires, the buck (rear right) and the battery leads (rear left).
  Mount the antenna vertically, above the chassis.
- Twist each motor lead pair. Add 100 nF across each motor at the motor if CRSF drops out.

## 7. Wiring and other notes

- **Motor terminals:** on both sides, the **front pad of each terminal is OUT_A**. Wire the same
  motor lead (e.g. red) to the front pad on every motor. Both motors on a side then turn the
  same way.
- **XT60s are vertical (AMASS XT60PB).** On both XT60s, pad 1 (bevelled end) is −. **Check this
  against your battery plug before soldering.** Q101 protects against reverse polarity, but the
  fuse path does not.
- **Power switch (J102), same XT60 footprint, two options:**
  - **Option A: external high-current switch.** An XT60 male lead to a DC switch rated
    **≥30 A at ≥24 V**, e.g. a rotary battery isolator or a high-current toggle.
  - **Option B: removable kill link.** An XT60 male with its pins shorted by ≥12 AWG. Pulling it
    kills VMOT, 5 V and the ESP32.
  - A 2.54 mm 2-pin header is **not** suitable for either: it's rated about 3 A.
- Q101's gate is fed from VMOT (after J102), so nothing loads the battery when switched off.
- **USB + battery:** check that your DevKit has a diode between USB VBUS and the 5V pin before
  plugging USB in while the battery is connected.
- **Header row spacing:** the ESP32 sockets are 25.4 mm apart. Measure your board and move J202
  if it reads 22.86 mm.
