# Plasma Ignition: revised architecture proposal (Rev B)

Danny's working document, 18 Oct 2026. Not for Vikas, and not sent. All values are first-pass engineering estimates (*derived*), not measurements.

## Summary of changes from the 15 Oct architecture

| Point | Was | Now |
|---|---|---|
| 1. Stage 1 edge | Two wound reactors targeting a 1–5 ns edge (realistically about 20–50 ns) | Three reactor stages, with the last one a single-turn coaxial ferrite reactor inside the plug cap. That gives about 2–5 ns rise, with an optional ferrite sharpening line for sub-ns |
| 2. Stage 2 voltage | 1 kV bank | **4 kV** bank aimed at **window B, about 2 µs** after breakdown |
| 3. Stage 1 caps | C1a of a few nF and C2a of 100 pF, which don't match | Equal referred capacitance of **100 pF** per stage at about 34 kV, about 58 mJ |
| 4. SRiso accounting | The spike "resets" the core, and the volt-seconds were simply added | The spike is the **opposite polarity** to the bank, the core is **bias-reset to −Bs** before each shot, and the spike and delay share one forward flux budget |
| 5. Energy delivery | 1 kV through 0.2–20 µH | SRiso's saturated inductance is the only series L, giving **Z0 ≈ 2 Ω**, with **reversal-rated** caps. The ringing tail is delivered into the hot channel in alternating polarity |
| 6. Edge leakage | Not budgeted | Single-layer wide-pitch SRiso winding in oil, about **1.5–3 pF**, with a loss of about 3–5 mJ (5–9%) budgeted |

## Block diagram (one plug)

```
48 V
 │
FRONT END (only solid state)
 controller · charger to 1.1 kV (C0a) and 4 kV (C0b) · one IGBT
 DC bias supply for every core (resets SR1–SR3 and SRiso to −Bs)
 energy recovery L + diode on C0a
 │                                   │
STAGE 1 (negative spike)          STAGE 2 (+4 kV)
C0a ≈ 96 nF @ 1.1 kV (58 mJ)      C0b 62.5 nF @ 4 kV (0.5 J)
 IGBT                               (125 nF for the 1 J ceiling)
pulse transformer 1:31               reversal-rated PP film, ≥6 kV
 → C1 100 pF, charged in ~1 µs        │
SR1 (81 µH saturated)         SRiso: N = 6, ≈8 cm² nanocrystalline,
 → C2 100 pF, ~200 ns                 9.5 mV·s budget, bias-reset to −Bs,
SR2 (3.2 µH saturated)                         L_sat ≈ 0.24 µH (no separate inductor)
 → C3 100 pF, ~40 ns                  │
   (10 MΩ bleed across C3)            │
SR3: single-turn coaxial ferrite,     │
     in the plug cap (hand: ~2–5 ns)  │
 │                                    │
C_block 1 nF, 60 kV pulse ───────── plug node ── non-resistor plug → head
                           (node sits at +4 kV between shots)
```

## 1. Stage 1 edge

- **Why two stages fell short.** Each wound stage compresses about 3–5×, so starting from about 1 µs, two stages land at about 50–100 ns. A 2–5 ns discharge from a 100 pF stage through a wound reactor would need a saturated inductance well under 50 nH.
- **The fix.** The final stage, SR3, discharges C3 (100 pF) into the plug and its local capacitance (about 15 pF), so the series C is about 13 pF. A 5 ns transfer needs only about 190 nH. A single-turn coaxial ferrite reactor of about 60 mm length (OD about 60 mm, ID about 25 mm) has a saturated L of about 10 nH, so the edge is set by the ferrite switching and the cap geometry, not by inductance. That was the hand argument for a **rise of about 2–5 ns**. The simulation did not support a single-turn hot NiZn SR3: no geometry that was tried holds off, and the full-chain cases that reach −42 to −44 kV have a 10–90% edge of 8.6–16 ns (report section 9.2).
- **Hold-off for SR3.** It holds C3's charging at about 34 kV × 40 ns × ½ ≈ 0.68 mV·s. With 1 turn at ΔB about 0.6 T (ferrite derated hot, with bias reset), that needs about 11 cm² of core area. The stack fits a cap about 70 mm across.
- **Ring-up at the gap.** It is 2·C3/(C3 + C_plug) ≈ 1.74×. A launch of 34 kV (1.1 kV × 1:31) gives a swing of about 59 kV. Less the 4 kV standing bias (see point 4), the hand estimate is **about −55 kV peak at the gap**, which keeps the 15 Oct worst case (1.0 mm, CR 10, ×1.1 × ×2). The simulation reaches **−51.1 kV with ideal SR1/SR2 and an ideal 10 nH SR3**, and **−40.3 kV with lossy SR1/SR2** and that same ideal SR3 (report section 9). Restoring −55 kV would be about +8% on stage 1 for the ideal chain (55/51.1) and about +37% for the lossy chain (55/40.3). Neither scale-up was resimulated (hand estimate / not simulated).
- **Sub-ns option (not baseline).** A ferrite-loaded sharpening line after SR3 could reach about 1 ns, but it costs line length, ferrite heat and energy. It needs about 0.3–1 m of line, which doesn't fit a plug well.

## 2. Stage 2 bank voltage and window

- **Window A (under 100 ns) is not achievable passively.** The SRiso delay is (remaining flux budget) ÷ bank voltage. Shot-to-shot jitter in the spike's volt-seconds (about ±0.3 mV·s) gives about ±75 ns of jitter at 4 kV, and about ±300 ns at 1 kV. That is larger than the whole window, so window A would need an active trigger.
- **Window B, re-derived.** The cold breakdown is about 25 kV × 1.1 ≈ 27.5 kV. At about 4000 K or hotter the channel density is about 13× lower, so it re-breaks at about **2.1 kV**. A **4 kV bank gives about 1.9× margin** (about 1.6× for a 1.2 mm gap).
- **Delay target.** About 2 µs. The channel is still hot then, and O and H radicals peak about 1 µs after the pulse. The volt-seconds are 4 kV × 2 µs = **8 mV·s**. The jitter of about ±75 ns is negligible against the 1–20 µs window.
- **Bank sizing.** 0.5 J at 4 kV is 62.5 nF, and the 1 J ceiling is 125 nF. The average charger load is about 75 W at 0.5 J and 150 pulses/s.

## 3. Stage 1 capacitor values

- The chain uses **equal referred capacitance**, so each transfer approaches 100%: C1 = C2 = C3 = 100 pF at about 34 kV, about **58 mJ per stage**.
- C0a = n² × C1 = 31² × 100 pF ≈ **96 nF at 1.1 kV**, which is also about 58 mJ and consistent.
- Transfer inductances for the target transfer times (series C = 50 pF): SR1 about 81 µH (200 ns) and SR2 about 3.2 µH (40 ns). The transformer charges C1 in about 1 µs. SR1 hold-off is about 34 kV × 1 µs × ½ ≈ 17 mV·s.
- Stage 1 averages about 9 W at 150 pulses/s. That is still millijoule-class per pulse, with margin above the about 1 mJ/mm spark threshold for compression losses.

## 4. SRiso volt-second accounting, made consistent

- **Rest state.** The bias winding resets SRiso to −Bs. The plug node sits at +4 kV with zero volts across SRiso, so nothing moves. Bias reset can run with the node live, because the node's few pF only shift by tens of volts while the core resets over about 1 ms.
- **Spike.** Stage 1 drives the node **negative**. The hand estimate is about −55 kV, so the voltage across SRiso is V_C0b − V_node ≈ +59 kV, the **forward** direction. It uses about 1.2 mV·s of forward flux (budget 1.5 mV·s with margin), and the core stays unsaturated, so it blocks. The +59 kV and 1.2 mV·s figures are that hand estimate. The simulated gap peaks are −51.1 kV (ideal cores) and −40.3 kV (lossy SR1/SR2, ideal SR3).
- **Delay.** After breakdown, the node falls to about 0 and SRiso sees +4 kV, still forward. It saturates after the **remaining** budget is used: 8 mV·s ÷ 4 kV = 2 µs.
- **Total budget.** 1.5 + 8 = **9.5 mV·s**, all in one direction, so adding them is now correct. N = 6 turns at ΔB about 2.0 T (nanocrystalline, derated hot) needs about **8 cm²**.
- **What was wrong before.** If the spike resets the core (a spike of the same polarity as the bank), the core must start near +Bs. The delay then equals the spike's own volt-seconds divided by the bank voltage, so it can't be set independently, and the bias can't also hold full reset.
- **Side effects of opposite polarity.**
  - Stage 1 must swing an extra 4 kV, which is covered in point 1.
  - The gap sees alternating polarity between the stages, which suits the balanced erosion idea.
  - A **DC block** (C_block about 1 nF, 60 kV pulse-rated doorknob) between SR3 and the node, plus a 10 MΩ bleed across C3, stops the standing 4 kV from charging C3 or biasing SR3. That resolves the earlier DC-coupling point.

## 5. Energy delivery into the channel

- **No separate series inductor.** SRiso's saturated inductance plus the loop is about 0.24 + 0.03 ≈ **0.27 µH**. With 62.5 nF that gives Z0 = √(L/C) ≈ **2.1 Ω** and a half-cycle of about **0.4 µs**.
- **First half-cycle delivery** into a channel resistance R:

| R (channel) | Delivered in the first half-cycle | Peak current |
|---|---|---|
| 0.5 Ω | ≈ 53% | ≈ 1.6 kA |
| 1 Ω | ≈ 78% | ≈ 1.3 kA |
| 2 Ω | ≈ 97% | 1.07 kA |

The 2 Ω peak is the exact series-RLC value. The earlier hand figure of about 0.9 kA was low. The simulation peak on that row is 1.02 kA. At 0.5 Ω and 1 Ω the exact RLC peaks are 1.61 kA and 1.38 kA, which the one-decimal hand figures already match; the simulation peaks are 1.53 kA and 1.32 kA.

- **The remainder.** It reverses the bank. The reverse voltage of about 1–3 kV drives SRiso back out of saturation, so it pauses for a few µs, then passes the next half-cycle in the opposite polarity while the channel is still hot. Most of the energy reaches the channel within about 10 µs. That is why **C0b must be PP film rated for 100% reversal** (or AC-rated), at 6 kV or more.
- **Trade-off.** A higher Z0 means lower current and less erosion, but more ringing. A lower Z0 means faster delivery but kA peaks. For the 1 J ceiling (125 nF), Z0 ≈ 1.5 Ω.

## 6. SRiso winding capacitance

- A single-layer, wide-pitch 6-turn winding in oil has a winding capacitance of about 1.5–3 pF. At a 2–5 ns edge (bandwidth about 70–175 MHz), 3 pF is roughly 300–750 Ω, which is high next to the stage 1 source.
- The energy lost into C0b is ½·Cp·V² at a 59 kV swing (the hand gap of −55 kV plus the 4 kV bank), about **2.6–5.2 mJ, or 5–9% of stage 1**. That is budgeted inside the 58 mJ. It was not recomputed for the simulated −51 kV / −40 kV peaks.
- The charge kicked into C0b is about 0.18 µC, which shifts it by only about 3 V and is negligible.
- If needed, split SRiso into two series sections with a grounded screen between them, which roughly halves Cp.

## Key numbers at a glance

- **Gap.** Hand estimate about −55 kV peak at 1.0 mm, CR 10. Simulated: −51 kV with ideal cores, −40.3 kV with lossy SR1/SR2 and an ideal SR3. The 2–5 ns rise is the hand target; see section 1. Stage 1 energy is about 58 mJ stored.
- **Stage 2.** +4 kV, 62.5 nF (0.5 J) up to 125 nF (1 J). Re-break needs about 2.1 kV, so the margin is about 1.9×.
- **SRiso.** The delay is about 2 µs, and the budget is 9.5 mV·s (N = 6, about 8 cm² nanocrystalline). Z0 is about 2.1 Ω, the half-cycle about 0.4 µs, and the peak is 1.07–1.61 kA (exact RLC; simulation 1.02–1.53 kA).
- **Average power at 150 pulses/s.** Stage 1 is about 9 W and stage 2 about 75 W (0.5 J).

## Remaining risks (not resolved by the maths alone)

- **Node behaviour during the 2 µs delay.** If the decaying channel stops conducting, SRiso's magnetising current pulls the node back toward +4 kV. That lowers the voltage across SRiso and stretches the delay, and the hot channel may partly re-break early at low current. That simulation has since been run; see `sim/RevB_simulation_report.md`.
- **Arc resistance and burning voltage at firing pressure** are unknown, and they set the delivery split in point 5.
- **The re-break scaling is rough**, using the ÷13 density at 4000 K.
- **Thermal derating at the cap** (100–150 °C), for both the ferrite in SR3 and SRiso.
- **Insulation.** SRiso carries about 10 kV per turn during the spike, which needs oil or potting and careful creepage.
- **Breakdown of HHO with water** is still bracketed only by the ×1.1 and ×2 margins.

## Suggested next calculations

1. Circuit simulation of the full chain with saturable-core models (SR1–SR3, SRiso, plug and channel models). Done after this note; see `sim/RevB_simulation_report.md`.
2. Firm up core materials and geometry hot, including the SR3 stack size inside the cap.
3. Engine data, which turns the CR 10 and 10° BTDC assumption into the real gap requirement.
