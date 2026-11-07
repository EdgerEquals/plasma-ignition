**Technical Handover — Plasma Ignitor Module for Honda GX120**
(First Prototype — Locked Design)

### 1. Project Overview
Compact, self-contained plasma ignition module that mounts over a stock spark plug on a Honda GX120. The goal is a reliable first-stage kernel (~100 mJ at 22–23 kV, 100–400 ns rise) for diluted HHO + water mist operation. All high-voltage parts are contained inside a 3" tri-clamp spool. Timing intelligence remains external.

### 2. Locked Design Summary
- **Engine**: Stock Honda GX120
- **Plug**: Stock BP6ES / BPR6ES (14 mm × 1.25, 19 mm reach)
- **Coaxial interface**: Outer copper sleeve contacts the head around the plug; inner tube + PTFE bushing contacts the plug terminal
- **Bottom adapter**: Carries the outer sleeve and provides the lower 3" tri-clamp flange
- **Enclosure**: 3" × 100 mm stainless tri-clamp spool with welded ferrules
- **Stack** (clamped by a single nylon M5 bolt):
  - Saturable reactor
  - Copper discs
  - Four parallel doorknob capacitors
  - Annular charger board (66 mm OD, 10 mm centre hole)
- **Charger**: 12 V flyback + 3-stage Cockcroft-Walton multiplier
- **Top plate**: 3" end plate with M8 4-pin IP67 bulkhead connector (12 V, ground, charge-enable, spare)
- **Potting**: High-voltage silicone or epoxy fills the spool
- **Control**: External MCU receives encoder data and sends only a charge-enable signal
- **Head modifications**: None required for the first prototype

### 3. Head Connection
- Stock plug is installed normally.
- Outer copper sleeve seats against the head around the plug boss (ground return).
- Bottom adapter + tri-clamp carries the rest of the module.
- No machining of the head is required to start.

### 4. Prototype Build Plan
1. Source/fabricate bottom adapter, top plate, 3" × 100 mm spool, clamps, gaskets.
2. Order annular charger board from PCBWay (BOM with datasheets attached).
3. Assemble coaxial interface over the installed plug.
4. Stack reactor, discs, capacitors, and charger board inside the spool.
5. Clamp with nylon bolt.
6. Connect low-voltage wiring to the M8 connector.
7. Pot the assembly.
8. Fit top plate and clamp.
9. Bench test charge to ~22–23 kV, then spark test, then engine test.

### 5. Status
- Mechanical architecture locked.
- Electrical architecture locked.
- BOM for the charger board expanded and datasheet-ready.
- First prototype build sequence defined.
- Ready for PCBWay and mechanical fabrication.

This document is the current single source of truth for the first prototype.