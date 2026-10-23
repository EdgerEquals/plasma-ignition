# Rev C – Design-out by margin

Working document. Not for external distribution.

Two-stage plasma ignitor, Rev B topology held fixed. No new circuit blocks. Stage-2 voltage, bank capacitance, SRiso iron and the SR3 winding were resized, and every move past 5% of the Rev B value is flagged. Engine is the Honda GX120. There is no bench here, so the three open items are closed by margin.

Scripts and numbers: `sim/run_revc.py`, results in `sim/results/revc/revc_summary.json`, plots in `sim/plots/revc/`. Engine is ngspice-39. Every figure below is marked **SIMULATED** (script name) or **HAND ESTIMATE**.

## 1. Summary

| Unknown | Assumed range | Source | Chosen size | Worst-case margin | Best-case margin | Kind |
|---|---|---|---|---|---|---|
| SR3, hot ferrite | µ 100–150; Sw 10–40 A·µs/m; ΔB 0.55–0.64 T; cap 25–120 °C | Ferroxcube 4C65 datasheet (µi 125 ±20%, Bs 380 mT at 25 °C and 340 mT at 100 °C). Sw bracket is the Rev B v2 sweep about the NBS 20 A·µs/m centre. Hot Bs floor 0.31 T taken as ΔB 0.55 T | 26 turns, 25 mm ID × 60 mm OD, stack 4.1 mm, 0.71 cm², Lsat 714 nH. Bias 359 A-t at the worst corner (includes +300 A/m) | Does **not** saturate. Analytical volt-second margin +50%, but the charge never reaches the knee. Full-chain gap **−25.8 kV**, 10–90% edge **45 ns** | Same hardware, still does **not** saturate. Full-chain gap **−26.5 kV**, 10–90% edge **56 ns** | SIMULATED `run_revc.py` |
| SRiso delivery | TTU-like 58% (this run **61%**) vs eddy 77%. JA 80% is the Rev B report, not re-run | `prs_model.py` models `ttu` and `eddy`. Xyce JA from `RevB_simulation_report.md` | 5.63 kV, 63.2 nF (**1.0 J**), N = 6, Ae 10.6 cm², Lsat 0.32 µH, 12.75 mV·s | TTU first half **575 mJ**, **+47%** over the 390 mJ target | Eddy first half **708 mJ**, **+82%**. JA not re-simulated | SIMULATED, except JA |
| Re-strike at ~2 µs | **0.98–3.75 kV** on the GX120 at 25° BTDC, 0.75 mm | Paschen fit from the 15 Oct handover, density at CR 8.5, channel-temperature bracket. Not a measured re-break | Bank **5.63 kV** (1.5× the worst end). No diode clamp in the run | Voltage margin **1.50×**. The quench run **does** re-break | Voltage margin **5.8×**. The quench run re-breaks | Voltage is HAND ESTIMATE. Re-break is SIMULATED |

The SR3 row is the one that does not close. Worst-case 4C65-class NiZn cannot be given a fast edge inside this cap. Section 2.1 says what µ and Sw would have to be, as a sensitivity, not as a new design.

## 2. Design-out by margin

### 2.0 What was re-run before anything was resized

Rev B values, unmodified. **SIMULATED** `run_revc.py` tags `revc_s1_ideal`, `revc_full_ideal`, `revc_full_lossy12`, `revc_st2_eddy_base`, `revc_st2_ttu_base`.

| Check | Rev B / report | This run | Difference |
|---|---|---|---|
| Stage-1 plug peak, ideal SR3 | −55.9 kV | −55.84 kV | −0.1% |
| Full-chain gap, ideal, no breakdown | −51.1 kV | −50.92 kV | −0.4% |
| Full-chain gap, lossy SR1/SR2 | about −40 kV (−40.3 kV in the v2 note) | −40.12 kV | −0.4% vs −40.3 |
| Eddy first-half delivery, 1 Ω | 77% | 76.7% | −0.4% |
| Eddy first-half current | 1.31 kA | 1.32 kA | +0.6% |
| TTU first-half delivery, 1 Ω | 58% | **61.4%** | **+5.8% — FLAG** |
| Leakage bound, 4C65, 25×80 mm, 190 nH | corrected figure about 47 A (the report's 25 A is withdrawn) | **49.1 A** from the same formula | about 4%, consistent with "~47 A" |

**FLAG, TTU 61% vs 58%.** Eddy lands on the report, so the metric (50 A crossing to the first current zero, stage-2 block, 1.5 mV·s already used by the spike) is the same one. The TTU gap is left as it is. It was not tuned. Likely causes: ngspice-39 versus the original run, and the stage-2 block rather than the full chain. 61% is the number used below.

**HAND ESTIMATE, not re-simulated.** From −40.1 kV to the −55 kV target is a 37% increase (55/40.1 − 1). An 8% increase on stage 1 does not get there. That matches the correction already in the brief. Lossy SR1 and SR2 are unchanged from `run_v2.py`: Lsat 81 µH and 3.2 µH, which are the Rev B transfer inductances (0% difference).

Component identity on these runs: every Rev B value in `prs_model.P` (C0a 96 nF, V0a 1.1 kV, n = 31, C1 = C2 = C3 = 100 pF, VS1 17 mV·s, VS2 3.4 mV·s, VS3 0.68 mV·s, L3s 10 nH, Cblock 1 nF, Cplug 15 pF, V0b 4 kV, C0b 62.5 nF, N = 6, Ae 8 cm², VSiso 9.5 mV·s, Lsat 0.24 µH) differs by **0%**.

### 2.1 SR3

**Temperature.** 25 °C is a cold start. 120 °C is a continuous 3600 rpm soak: GX120 oil is allowed to run hot, the plug hex sits on the head, and the cap is outside the chamber. 120 °C is below the 4C65 Curie point (≥ 350 °C). The October handover's 150 °C is a further derate and was not used for the size.

**Range, and which end is worst.**

| Quantity | Worst | Best | Where it comes from |
|---|---|---|---|
| µ | 100 | 150 | 4C65 datasheet, µi = 125 ±20% at 25 °C. Fig. 2 (µ vs temperature) was not digitized, so hot µ was not credited as higher. The floor is the worst hold-off |
| Sw | 40 A·µs/m | 10 A·µs/m | Centre 20 A·µs/m is the Rev B citation (NBS, about 0.25 Oe·µs; KEK/CAT about 3 Oe for 100 ns). The factor-of-two band is the v2 sweep. Assigning the high Sw to the cold end is a **HAND ESTIMATE**: walls get faster as they warm. There is no hot Sw datasheet |
| ΔB, bias reset | 0.55 T | 0.64 T | Worst: Bs 0.31 T hot (the brief's floor; 4C65 measures 340 mT at 100 °C, straight-line to 120 °C is about 330 mT, so 0.31 T is slightly past the line). Usable swing taken as the repo's 0.60/0.34 fraction of Bs. Best: 25 °C, Bs 380 mT, swing 0.64 T. **HAND ESTIMATE** on the fraction |
| Hc | 200 A/m | 200 A/m | Already assumed in `run_v2.py`. Not a datasheet number |

Worst corner stacks the bad ends on purpose (low µ, high Sw, low ΔB). They are not one temperature.

**Hold-off arithmetic (HAND ESTIMATE, checked).** H at full swing = ΔB/(µ0 µ) + Sw/40 ns + Hc. The bound I_leak · Lsat = (µ0/2π) · H · (VS/ΔB) · (le/hw) · ln(b/a) does not improve by adding turns at a fixed Lsat. On the report's 25×80 mm 4C65 reference it gives **49 A at 190 nH**, which is the corrected ~47 A, not 25 A.

**Chosen hardware**, smallest turn count inside a 4–20 mm stack with that bound ≤ 20 A, on the 25×60 mm tube that fits the ~70 mm cap:

- 26 turns, OD 60 mm, ID 25 mm, length 4.1 mm, iron 0.71 cm²
- Lsat **714 nH** (Rev B single-turn figure is 10 nH)
- Volt-seconds at the worst ΔB: **1.02 mV·s**, which is 1.50× the 0.68 mV·s the chain applies (34 kV × 40 ns × ½)
- Bias, worst corner: **359 A-t**. Formula is the repo one: (ΔB/(2 µ0 µ) + Hc + 300 A/m) × le. Best corner, same winding: 293 A-t

| SR3 value | Rev B | Simulated hardware | Difference |
|---|---|---|---|
| Turns | 1 (coax) | 26 | **FLAG, +2500%** |
| Lsat | 10 nH | 714 nH | **FLAG** |
| Volt-second rating at worst ΔB | 0.68 mV·s | 1.02 mV·s | **FLAG, +50%** |
| C1, C2, C3, VS1, VS2, transformer, C_block, C_plug | Rev B | unchanged | 0% |

**SIMULATED** (`revc_sr3_worst_*`, `revc_sr3_best_*`, `revc_sr3_worst_full_lossy12`).

| Corner | Saturates? | C3 peak | Gap, full chain, ideal SR1/SR2 | 10–90% edge | 50–90% edge | λ reached |
|---|---|---|---|---|---|---|
| Worst | No | −31.3 kV | **−25.8 kV** | **45 ns** | 23 ns | 0.69 mV·s of 1.02 available |
| Best | No | −32.3 kV | **−26.5 kV** | **56 ns** | 28 ns | 1.02 mV·s of 1.19 available |
| Worst + lossy SR1/SR2 | — | — | **−22.4 kV** | 48 ns | 22 ns | — |

C3 does charge (about −31 kV against a 34 kV ideal). The core then never reaches its own knee, because the iron was sized 50% past the volt-seconds the chain actually delivers, and what leaks never comes back. The plug still moves, but in 45–56 ns, which is the SR2 window. SR3 is not compressing. Against a GX120 cold break of about 14 kV (**HAND ESTIMATE**, §2.3) the gap voltage still fires. It does not make −55 kV, and with lossy SR1/SR2 it does not make −40 kV either.

**FLAG. This size meets the leakage bound and the volt-second margin, and it still does not switch.** No other 4C65-class geometry inside the cap fixes both leakage and saturation at once: more turns at this µ cuts leakage only by raising Lsat and thinning the stack until it is not a core.

**Sensitivity, not a design change** (`revc_sr3probe_*`). Same circuit, hypothetical NiZn, 12 turns, 25×60 mm.

| Probe | Saturates | Full-chain gap | 10–90% | 50–90% |
|---|---|---|---|---|
| µ 1000, Sw 10 A·µs/m, ΔB 0.55 T | Yes | −40.6 kV | 20 ns | 2.2 ns |
| µ 2000, Sw 5 A·µs/m, ΔB 0.55 T | Yes | −45.3 kV | 4.4 ns | 1.9 ns |

The fast number is the 50–90% slice. The 10–90% edge is 4–20 ns. That sits with the correction in the brief (full-chain 10–90% about 8.6–16 ns; the old 1.3–1.6 ns was 50–90%). Neither probe is adopted. Both say the same thing: SR3 needs a measured hot µ around 1000–2000 and an Sw at or under 5–10 A·µs/m, which 4C65 does not have.

### 2.2 SRiso

**Enough**, taken from the Rev B proposal and not inflated. At 1 Ω the hand table is 78% of the 0.5 J bank in the first half-cycle: **390 mJ**. The "most of it within 10 µs" line is extra, and it is reported, but the size is set by the first half on the pessimistic model.

**Baseline, Rev B bank, SIMULATED.**

| Model | First half | 10 µs | Peak current | Reversal |
|---|---|---|---|---|
| Eddy | 371 mJ (76.7%) | 453 mJ | 1.32 kA | 48% |
| TTU | 291 mJ (**61.4%**) | 408 mJ | 1.01 kA | 65% |
| JA | — | — | 1.34 kA and 80% in the Rev B report | not re-run |

**FLAG. Xyce is not in this environment, so the Jiles–Atherton model was not re-run.** The 77–80% pair in the brief is eddy (re-run, 77%) plus the published JA result (80%).

TTU's first half, 291 mJ, misses 390 mJ. Its 10 µs integral, 408 mJ, only just clears it. The first half is the quantity that arrives while the channel is hottest, so that is the one that was sized.

**Why the voltage also moves.** Section 2.3 sets the bank to 5.63 kV so the worst re-break still has 1.5× in hand. At 5.63 kV a 0.5 J bank is only 31.6 nF, and the TTU first half falls to 202 mJ (tag `revc_st2_ttu_a0`). Higher voltage at fixed energy raises Z0 and the pessimistic model delivers less. Capacitance was then raised until the first half cleared 390 mJ with real margin, stopping at the proposal's own **1 J ceiling**.

**Chosen SRiso and bank. SIMULATED** `revc_st2_ttu_C63n2`, `revc_st2_eddy_C63n2`.

- V0b = **5626 V**
- C0b = **63.2 nF** (stored energy 1.00 J)
- N = 6, unchanged
- Forward budget = 1.5 mV·s spike + 5.626 kV × 2 µs = **12.75 mV·s**
- Ae = 12.75 mV·s / (6 × 2.0 T) = **10.63 cm²**
- Lsat = 0.24 µH × (10.63/8) = **0.319 µH** (scales with area; mean path held at the Rev B 0.22 m)
- Delay comes back at 2.00 µs (eddy) and 2.20 µs (TTU). Still the 2 µs window

| Value | Rev B | Chosen | Difference |
|---|---|---|---|
| V0b | 4.00 kV | 5.63 kV | **FLAG, +41%** |
| C0b | 62.5 nF | 63.2 nF | +1.1%, inside 5% — **do not read this as "no change"** |
| Stored energy | 0.50 J | 1.00 J | **FLAG, +100%.** The 1% capacitance move is a coincidence: 1 J at 5.63 kV needs almost the same nanofarads as 0.5 J at 4 kV |
| VSiso | 9.5 mV·s | 12.75 mV·s | **FLAG, +34%** |
| Ae | 8.0 cm² | 10.6 cm² | **FLAG, +33%** |
| Lsat | 0.24 µH | 0.32 µH | **FLAG, +33%** |
| N, Lloop 30 nH, Cw 1.5 pF, R = 1 Ω | Rev B | unchanged | 0% |

| Model | First half | Margin on 390 mJ | 10 µs | Current | Reversal |
|---|---|---|---|---|---|
| TTU, worst | **575 mJ** | **+47%** | 808 mJ | 1.37 kA | 65% |
| Eddy, best of the two that were re-run | **708 mJ** | **+82%** | 896 mJ | 1.71 kA | 52% |

A 50 nF / 0.79 J intermediate was also run. TTU first half there is 408 mJ, only +5% over 390 mJ. That is not a margin. The 1 J point is the one that earns it. It is the ceiling the proposal already allowed (125 nF at 4 kV), reached here by voltage rather than by more capacitance.

Reversal at the 1 J eddy run is 52%, so the bank swings to about −2.9 kV. The proposal's "≥ 6 kV, 100% reversal" rating was for a 4 kV bank. **FLAG.** Rate this film for **≥ 9 kV and 100% reversal**. A 6 kV part is under the 5.63 kV charge before any spike.

### 2.3 Re-strike

No diode clamp in any of these runs. The clamp rail in the Rev B follow-up was an ideal source and its PIV was not modelled; that is unchanged, and it is not what re-strikes the gap here.

**Cold breakdown, HAND ESTIMATE.** Handover fit V(kV) = 24.22·δd + 6.08·√(δd), d in cm, δ relative to 293 K and 1 atm. GX120: bore 60 mm, stroke 42 mm, Vd = 118.8 cc, CR 8.5, Vc = 15.8 cc, rod ratio 3.5, polytropic 1.30, intake 0.95 atm and 320 K. At 25° BTDC (stock magneto timing): firing volume 22.9 cc, pressure 9.5 atm, temperature 544 K, δ = 5.11. Gap 0.75 mm.

- Air: **13.1 kV**
- ×1.1 for the HHO / water mix, the handover's factor: **14.4 kV**

At 20° BTDC the same sum is 15.9 kV. The 25° number is the one used.

**Channel at about 2 µs, HAND ESTIMATE.** Isobaric kernel, so voltage scales as T_fire / T_channel. This is the Rev B ÷13 idea, done at the firing temperature instead of at 300 K.

| End | T_channel | Extra factor | Re-break | Why this end |
|---|---|---|---|---|
| Best | 8000 K | none | **0.98 kV** | Core still hot at 2 µs. Wang-class data (handover) still see ~4000 K at 10 µs at about 1 atm, so 8000 K at 2 µs is a hot core, not a measurement |
| Mid | 4000 K | none | **1.95 kV** | Same 4000 K held all the way to 2 µs. Rev B's 2.1 kV was 27.5 kV/13 for a 1.0 mm, CR 10 gap referred to 300 K. On this engine that method gives 1.95 kV, not 2.1 kV |
| Worst | 2500 K | ×1.2 | **3.75 kV** | Cooled kernel at ~9.5 atm, where three-body quenching is faster than the 1 atm papers, plus attachment to O2 and H2O. The ×1.2 is a judgement, not a paper |

Literature does not give a GX120 number at 2 µs. Atmospheric spark-gap recovery (Chan; high-energy gap papers) is still early at 2 µs: most of the dielectric strength comes back over 100 µs to milliseconds at 1 atm. That supports "well below the 14 kV cold break." It does not support a single value. The bracket is the design range. **FLAG: the worst end is a bracket, not a measurement.**

**Chosen bank voltage: 5.63 kV = 1.5 × 3.75 kV.** Rev B's 4.00 kV is only 1.07× the worst end.

**SIMULATED, no clamp, quench at +1 µs, eddy full chain.**

| Bank | Re-break threshold | Re-breaks? | SRiso delay | Reversal | First-half current |
|---|---|---|---|---|---|
| 4.00 kV, 62.5 nF | 3.75 kV | Yes, ~30 ns after the quench | 2.40 µs | 48% | 1.32 kA |
| 4.00 kV, 62.5 nF | 0.98 kV | Yes | 2.37 µs | 48% | 1.32 kA |
| **5.63 kV, 63.2 nF** | **3.75 kV** | **Yes** | **2.27 µs** | **52%** | **1.71 kA** |
| **5.63 kV, 63.2 nF** | **0.98 kV** | Yes — the 3.75 kV run crosses 0.98 kV on the way up, so the easier threshold is met on that same waveform | 2.27 µs | 52% | 1.71 kA |

So 4 kV does re-break inside this model, including at 3.75 kV. The node is pulled toward the bank by SRiso's magnetising current as soon as the channel quenches. The margin on that result is 7%. That is not designed out. 5.63 kV is.

Knock-on, all flagged in §2.2: bank energy to the 1 J ceiling, SRiso iron +33%, Lsat +33%, film rating from ≥6 kV to ≥9 kV, reversal still about half so the reverse peak is −2.9 kV rather than a full swing. The 2 µs delay was preserved by resizing the volt-second budget with the voltage; it was not left at 9.5 mV·s.

## 3. Core material recommendations (no design change)

Nothing in this section changes the size above.

**SR3 has to be fast, and it sits in the cap.** The material wants high resistivity more than it wants flux. NiZn is the right family (ρ about 10^5 Ω·m). Metallic tape is the wrong one here: FINEMET, Vitroperm, and Metglas 2605SA1 / 2605CO / 2714A will eddy-current at a few nanoseconds unless the tape is vanishingly thin, and a wound core is not the coax switch this position is. MnZn (3C95, N87 and the like) has the permeability and then loses it to conductivity, and many of those grades are already giving up Bs by 120 °C.

Inside NiZn, 4C65 and 4B1 are what §2.1 sized, and they do not switch. CMD5005 has the permeability (µi about 2100) and the wrong Curie point (about 130 °C): no margin at a 120 °C soak. The grade worth buying and measuring is a pulse NiZn with µi still around 1000 at 120 °C, Bs still around 0.35 T, and Tc ≥ 200 °C. National Magnetics CMD10 (µi about 625, Tc 250 °C) is the closest catalogue part named in the Rev B note. Fair-Rite 67 (µi 40) is worse than 4C65. Do not change the winding on the back of a catalogue µi. Measure Sw and hot µ on a 40 ns, ~0.5 T pulse.

**SRiso is a microsecond, kiloamp core. Nanocrystalline stays the right answer.** FINEMET (Hitachi) or Vitroperm 500F (Vacuumschmelze): Bs about 1.2 T, so a 2.0 T bias-reset swing is the right order, coercivity a few A/m, and 120 °C costs a modest slice of Bs rather than the Curie point. That is why the iron only grew by a third when the voltage went to 5.63 kV. The entire TTU-versus-eddy argument is the rate-dependent loss of this class of core. A different catalogue will not settle it.

Amorphous 2605SA1 (Metglas) has more Bs (about 1.56 T) and more loss and magnetostriction; it is a fallback if a nanocrystalline core of 11 cm² cannot be had. 2714A is quieter and only about 0.57 T, so the core gets large. Ferrite at ΔB ~0.5 T needs about four times the area and will not enjoy 1.7 kA. Keep SRiso nanocrystalline. Buy the core, pulse it at kA, and let that measurement pick the model.

Suppliers, for the purchasing list only: Ferroxcube (4C65, 4B1), National Magnetics / Magnetics (CMD10, CMD5005), Fair-Rite, Hitachi Metals (Finemet), Vacuumschmelze (Vitroperm), Metglas (2605SA1, 2714A).

## 4. Open risks, and the one measurement that would retire each

1. **SR3 never switches on worst-case NiZn.** One pulse on the candidate core at 120 °C, about 40 ns and 0.5 T, measuring µ and Sw. If Sw ≤ 10 A·µs/m and µ ≥ 1000, the sensitivity in §2.1 is the core to wind. If not, SR3 stays a 45 ns pass-through and the −55 kV edge is not available.
2. **TTU 61% versus eddy 77% (JA 80% not re-run).** One kiloamp, few-microsecond pulse on the real SRiso core into a resistive load. That is the measurement the Rev B report already asked for.
3. **Re-break bracket 1–4 kV.** One double pulse, either in a pressurised gap at ~9 atm and ~540 K or on the GX120 with a sense resistor, delay about 2 µs. Until then the 5.63 kV bank is carrying a bracket, not a measured margin.
4. **Lossy SR1/SR2 hold the gap at −40 kV before SR3 makes it worse.** One stage-1 shot into a dummy load with the real SR1 and SR2 cores. Retires the −51 versus −40 kV split.
5. **Clamp, if it is built later.** The Rev B clamp was an ideal voltage source. PIV, stored charge and capacitance were not modelled. This study does not use it, and the re-strike result must not be read as depending on it.
6. **HHO plus water vapour at firing pressure.** Still only the ×1.1 on the cold break and the ×1.2 on the worst re-break. Same measurement as item 3, done in the real mix, retires both.

## 5. Plots, scripts, files

Plots, all from `run_revc.py` and the plot pass that follows it:

- `sim/plots/revc/revc_sr3_edge.png` — ideal SR3 against the sized worst and best corners, plus the µ 2000 sensitivity.
- `sim/plots/revc/revc_sriso_energy.png` — channel energy at 1 Ω, Rev B bank against the 1 J / 5.63 kV bank, eddy and TTU.
- `sim/plots/revc/revc_restrike_node.png` — plug node after a 1 µs quench, 4 kV bank against the sized bank, no clamp. The dashed line is the 3.75 kV worst re-break.

Files:

- `sim/run_revc.py` — the study. Re-runnable. Checkpoints to `sim/results/revc/checkpoint.jsonl`.
- `sim/results/revc/revc_summary.json` — validation, SR3 corners, re-strike bracket, audit flags.
- Probe and final-bank runs are in `sim/netlists/revc_*.cir` and `sim/out/revc_*.dat`.
- Model code is the Rev B `sim/prs_model.py`. No equation was changed.

Component-check tables are in §2.0, §2.1 and §2.2. Flags are the SR3 winding, the 5.63 kV bank, the 1 J stored energy, the SRiso iron and Lsat, the 9 kV film rating, the TTU 61% versus 58% disagreement, and the JA model not being re-run.
