# PRS Rev B: circuit simulation report

Danny's working file, 18 Oct 2026. Not for Vikas, and not sent. Every number below comes from a simulation run on the box, or from the Rev B proposal (`../PRS_RevB_architecture_proposal.md`) where it is labelled "hand". The simulations are lumped-element models with assumed core models. They are not measurements.

## 1. Bottom line

> **v2 update (19 Oct 2026), see section 9.** Quench without re-break: recommend a diode clamp to a 4.4–5 kV reservoir rail (node ≤ 6 kV, no normal-shot cost, −1 kV of spike). SR3: hot NiZn at ≤ 190 nH does not hold off (gap −24 to −28 kV); it needs µ ≥ 1000–2000 and Sw ≤ 5–10 A·µs/m, to be measured. C_block: the residual ratchets with a low-loss transformer; fix with 100–300 kΩ from the SR3 output to ground. Realistic SR1/SR2 losses alone cut the gap peak from −51 to −40 kV.

1. **The Rev B hand numbers hold up when each block is checked on its own.**
   - Transfer times are within 2% (1.0 µs, 197 ns, 39 ns, and 4.8 ns with SR3 at 190 nH).
   - The SRiso delay matches V·s ÷ 4 kV to within 0.3%.
   - First-half-cycle delivery is 51 / 77 / 96% (hand: 53 / 78 / 97%).
   - Peak currents are 1.53 / 1.32 / 1.02 kA (hand: 1.6 / 1.3 / 0.9 kA).
   - The hand figure of 0.9 kA at 2 Ω is itself about 15% low. The exact series RLC gives 1.07 kA.
2. **The delay comes out at about 2.36–2.37 µs, not 2 µs, with the 9.5 mV·s budget.**
   - The spike only uses about 0.14–0.18 mV·s, not the 1.2–1.5 mV·s that was budgeted. With SR3 saturating at about 10 nH, the gap only sees full voltage for a nanosecond or two.
   - With the real hot flux swing of nanocrystalline (≈2.26–2.38 T at 120 °C instead of the 1.98 T design value), the delay grows to **2.7–2.9 µs**.
   - Both are still well inside window B (1–20 µs). If 2 µs matters, set it by core area or turns, or trim the bias reset point.
   - ±20% spike jitter moves the delay by only ±7–9 ns, or ±60 ns if the spike really were 1.2 mV·s.
3. **The node risk flagged in the proposal is real, and quench is the case that matters.**
   - **If the channel keeps conducting** (0.5–2 Ω), the node stays near 0. The only exceptions are narrow ±0.4–1.1 kV spikes from stage-1 ringing. SRiso sees 3–4 kV and fires on schedule.
   - **If the channel quenches but re-breaks at about 2.1 kV** (the doc's hot-channel figure), the node climbs to 2.1 kV within **≈20–40 ns** of the quench and re-breaks. The current after re-break is only about **1.5–1.8 A** (median; SRiso magnetising current). The delay stretch is negligible (+5–10 ns).
     - So the circuit itself forces an early, low-current re-break.
     - Whether a decaying channel actually re-strikes and carries about 2 A is plasma physics, and this model cannot answer it.
   - **If the channel quenches and does NOT re-break** (cold), every core model says SRiso never fires on schedule. Within about 0.1 µs the node rises to +4 kV and then rings far beyond it:
     - 10–15 kV with the eddy-current model
     - 30–34 kV with TTU in ngspice and LTspice
     - about 34 kV with Xyce Jiles–Atherton

     That means a misfire, or an uncontrolled late breakdown at the wrong time. **This is the main design risk the simulation exposes.**
4. **Spike leakage into the stage-2 branch is within budget.**
   - Peak energy absorbed by the SRiso/C0b branch during the spike:
     - 0.6–0.75 mJ (1.1–1.3% of 58 mJ) for breakdown at 27.5 kV
     - 2.5 mJ (4.3%) for breakdown at the peak, with Cw = 1.5 pF
     - 4.3 mJ (7.5%) for breakdown at the peak, with Cw = 3 pF
   - The doc budget is 5–9%. The C0b kick is 1–1.3 V (the doc estimated about 3 V).
5. **The core model decides how energy is delivered, but not the delay. This triggered the Xyce check.**
   - The square-loop + eddy model (ngspice, primary) and the TTU model differ by more than 15% on first-half-cycle energy.
     - TTU in LTspice and the ngspice port agree within 1%.
     - At R = 1 Ω: 77% for square-loop + eddy against 58% for TTU.
   - Xyce with a Jiles–Atherton core (stage-2 block) sides with the eddy model: 80% / 1.34 kA at 1 Ω, against eddy 77% / 1.31 kA.
   - The TTU shortfall comes from its soft saturation knee. That knee is made worse because the TTU model latches the spike's dB/dt into the stage-2 pulse, which is outside what it was validated for. The core then swallows about 1–1.5 mV·s beyond the knee while current is flowing.
6. **SR3 as an "ideal" switch is the weakest assumption in the chain.**
   - With a realistic unsaturated inductance for a single-turn ferrite (about 5 µH, pulsed NiZn µr ≈ 500), SR3 **never saturates**. The plug just follows C3 with a 23 ns edge and reaches −45 kV.
   - The 2–5 ns edge needs about 50 µH or more unsaturated on one turn, roughly µr ≥ 5000. The ferrite choice and test are the gating item.

## 2. Method

- **Simulators.**
  - ngspice 44.2 (Debian), batch mode, driven from Python (`prs_model.py`, `analysis.py`, `run_all.py`).
  - LTspice 26.1.1 (Windows build, run headless under Wine 10 on the box with `-b -ascii`).
  - Xyce 7.9.0, built from source on the box against Trilinos 14.4, also built from source. Debian's Trilinos 13.2 was too old.
  - Everything reruns with `python3 run_all.py`. Use `--no-lt` or `--no-xyce` to skip those, and `--patch` to redo the validation and the cases fixed after the first run.
- **Breakdown is multi-pass.**
  - Pass 1 runs with no channel and finds when the plug crosses −27.5 kV (the doc's cold 25 kV × 1.1) or its negative peak ("bd at peak", the worst-case design point).
  - Pass 2 closes the channel at that time with a 1 ns ramp to R.
  - Quench reopens the channel at +0.5, 1.0 or 1.5 µs.
  - Re-break (when enabled) recloses it the first time |V_node| exceeds 2.1 kV (pass 3).
- **Metrics.**
  - Delay: breakdown until SRiso current exceeds 50 A.
  - First-half-cycle delivery: channel energy from saturation to the first current zero, divided by bank energy at saturation.
  - Spike leakage: peak of ∫V_node·I_branch over the spike window.
  - Reversal: the most negative C0b voltage ÷ 4 kV.

### Circuit (all values from Rev B unless marked ASSUMED)

| Part | Model |
|---|---|
| C0a 96 nF at 1.1 kV, IGBT | Cap with initial condition; IGBT is an ideal diode (one-way, no energy recovery modelled) |
| 1:31 pulse transformer | Coupled L, k = 1, Lm = 1 mH primary (ASSUMED); leakage 2.1 µH set for a 1 µs charge of C1. No core saturation |
| C1 = C2 = C3 = 100 pF; 10 MΩ bleed on C3 | as doc |
| SR1, SR2 | Lossless piecewise saturable L: Lsat 81 µH and 3.2 µH (doc's transfer inductances), Lunsat = 1000 × Lsat (ASSUMED; 300× tested), reset to the reverse knee. Hold-off 17 mV·s (doc) and 3.4 mV·s (same ½VT rule) |
| SR3 | "Ideal" saturating L per brief: Lsat 10 nH (190 nH tested), Lunsat 1 mH (5 µH tested), 0.68 mV·s |
| C_block 1 nF, plug 15 pF | Node rests at +4 kV; C_block pre-charged to 4 kV |
| C0b 62.5 / 125 nF at 4 kV | Ideal film cap |
| SRiso | N = 6, Ae = 8 cm², le = 22 cm (ASSUMED), 9.5 mV·s forward budget from −Bs, 0.24 + 0.03 µH saturated in series, Cw 1.5 pF (3 pF tested). Core models in section 3 |
| Channel | Time-switched conductance 1/R, R = 0.5, 1 or 2 Ω, constant. No arc burning voltage and no R(t) |

## 3. Core models (SRiso)

1. **Primary (ngspice): square loop + eddy current.**
   - Flux is integrated from the core voltage. H = Hc·tanh(·) + kₑ·dB/dt between the reset point and +ΔB, with steep saturation walls on both sides.
   - Hc = 2.5 A/m (FINEMET FT-3M catalogue).
   - kₑ = 4.5×10⁻⁵ A·s/(m·T). That is the classical d²/12ρ for 18 µm ribbon at 1.2 µΩ·m, times an ASSUMED excess factor of 2. Values of ×0.5 and ×2 were tested.
   - The magnetising current during the delay comes out at about 1.4–2 A.
2. **TTU behavioural model (Kelp et al., Texas Tech).** It was downloaded from p3e.ttu.edu, run unmodified in structure in LTspice, and ported equation-for-equation to ngspice. Its FT-3KM parameter set (k1 = 5e-5, k3 = 8, Γ = 0.21; R = 200 Ω and C = 0.8 nF) was scaled by N²·Ae/le to this core. Two changes were needed and are stated plainly:
   1. The model's μ(B) is symmetric about B = 0 (a demagnetised core). It was **re-centred** (`ut(B−Bc)`, Bc = ΔB/2), with k2 rescaled so the knees sit at −0.05 T and ΔB + 0.05 T. This represents the bias reset to −Bs. Adding a DC bias to the TTU model as shipped does not work, because its rate factor α moves the operating point.
   2. In the top-level netlist, `.model D D` was added because the LTspice 26 libraries were not auto-loaded under Wine.

   The TTU model is validated for 0.5–8 T/µs. Here the delay runs at about 0.8 T/µs, but the spike reaches about 7–12 T/µs, and the model's 10 ms peak-rate latch carries that rate into the stage-2 pulse. A "no latch" variant (20 ns smoothing) was also run. It is numerically noisier.
3. **Xyce Jiles–Atherton** (MutIndNonLin `CORE`), on the stage-2 block only.
   - Ms = 7.2×10⁵ A/m, a = 4, k = 3, c = 0.05, α = 3.5×10⁻⁶. These were calibrated with a 1 kHz B–H loop run on the box to Bs ≈ 1.19 T (120 °C) and Hc ≈ 2.5 A/m.
   - It is rate-independent, so it has no eddy loss.
   - The reset comes from a 1-turn bias winding driven by an ideal −60 A/m DC source, ramped over 100 µs before the shot. The loop is not square (Br/Bs ≈ 0.4), so the core only reaches −0.85 T. Its available forward swing is about 1.8 T and its delay 2.13 µs, so its delay is not comparable one-to-one.

**Cross-check results (R = 1 Ω, 62.5 nF, breakdown 27.5 kV, full chain except Xyce):**

| Model | Delay µs | 1st half-cycle % | Ipk kA | C0b reversal % |
|---|---|---|---|---|
| Square loop + eddy (ngspice, primary) | 2.371 | 76.6 | 1.31 | 48 |
| TTU port (ngspice) | 2.545 | 57.7 | 0.87 | 74 |
| TTU original (LTspice/Wine) | 2.545 | 58.1 | 0.87 | 74 |
| TTU port, no rate latch | 2.580 | 63.5 | 1.69 (noisy) | 69 |
| Xyce JA (stage-2 block) | 2.13 (1.8 T swing) | 80.2 | 1.34 | 51 |

- **Port vs original:** the ngspice TTU port matches the original in LTspice within 0.1% on delay and within 0.7% on energy and current across all 6 baseline cases and both quench cases.
- **Delay:** the primary and TTU models differ by 7%. The TTU delay is longer because its soft knee places "saturation" about 0.05 T past ΔB.
- **Energy:** they differ by 25% at 1 Ω, 28% at 0.5 Ω and 16% at 2 Ω. That is above the 15% trigger, so Xyce was run.
- **Xyce verdict:** JA agrees with the eddy model within 4% on delivery and 2–5% on peak current at all three R values (0.5 Ω: 54% / 1.56 kA; 2 Ω: 98% / 1.04 kA).
- **Conclusion:** the low TTU delivery is put down to its latched-rate soft knee rather than a solver issue. Bench measurement of a real core at kA is still the only real arbiter.

## 4. Block validation (sim vs hand)

| Block | Quantity | Hand | Sim | Error |
|---|---|---|---|---|
| Transformer | C1 charge time | 1000 ns | 990 ns | −1.0% |
| Transformer | C1 peak | 34.1 kV | 33.5 kV | −1.8% |
| SR1 | transfer (saturation → C2 peak) | 200 ns | 197 ns | −1.3% (fires 17 ns after C1 peak) |
| SR1 | C2 peak | 34.1 kV | 32.9 kV | −3.6% |
| SR2 | transfer | 40 ns | 39.4 ns | −1.4% |
| SR2 | C3 peak | 34.1 kV | 32.9 kV | −3.6% |
| SR3, 10 nH | C3 → plug, to 98% | "2–5 ns" | 1.1 ns (10–90% 0.74 ns) | ideal L only; ferrite switching time not modelled |
| SR3, 190 nH | C3 → plug, to 98% | 5 ns | 4.76 ns | −4.8% |
| SR3 + plug | ring-up | 1.74× | 1.69× | −2.7% (hand incl. C_block + Cw = 1.693×) |
| SR3 + plug | swing | 59 kV | 55.5 kV | −5.9% |
| Full chain | node at peak (−swing + 4 kV bias) | −55 kV | **−51.1 kV** | −7% |
| SRiso | delay, 1.5 mV·s spike preset | 2000 ns | 1995 ns | −0.3% |
| SRiso | delay, no spike | 2375 ns | 2376 ns | +0.05% |
| SRiso + C0b | Z0 | 2.08 Ω | 2.19 Ω | +5.5% (core transition at saturation onset) |
| SRiso + C0b | half-cycle | 408 ns | 456 ns | +12% (measured from the 50 A crossing; soft onset) |
| Delivery 0.5 / 1 / 2 Ω | 1st half-cycle | 53 / 78 / 97% | 51.4 / 76.7 / 95.5% | −3.1 / −1.6 / −1.5% |
| Peak 0.5 / 1 / 2 Ω | Ipk | 1.6 / 1.3 / 0.9 kA | 1.53 / 1.32 / 1.02 kA | −4 / +1 / **+13%** (exact RLC 1.61 / 1.38 / 1.07) |
| Winding C | ½CwV², Cw 1.5 / 3 pF | 2.6 / 5.2 mJ | 2.27 / 4.43 mJ | −13 / −15% (swing is 55 kV, not 59) |

The full table, with notes, is in `results/tables.md`.

## 5. Sweep results (primary model, 62.5 nF unless stated)

| Case | Spike V·s mV·s | Delay µs | Node max in delay | SRiso min in delay | 1st half % | Ipk kA | C0b reversal | E to channel (13 µs) |
|---|---|---|---|---|---|---|---|---|
| bd 27.5 kV, R 0.5 / 1 / 2 Ω | 0.14 / 0.14 / 0.15 | 2.371 | 0.4 / 0.6 / 1.1 kV spikes | 3.6 / 3.3 / 2.9 kV | 51 / 77 / 96 | 1.53 / 1.31 / 1.02 | 69 / 48 / 22% | 435 / 476 / 493 mJ |
| bd at peak (−51 kV), R 0.5 / 1 / 2 Ω | 0.17–0.18 | 2.362 | similar | 3.6 / 3.4 / 2.9 kV | 52 / 77 / 96 | 1.53 / 1.32 / 1.02 | 69 / 48 / 22% | 444 / 483 / 496 mJ |
| 125 nF (1 J), bd 27.5 kV, R 0.5 / 1 / 2 Ω | 0.14 | 2.360 | similar | — | 65 / 88 / 99.5 | **2.06** / 1.69 / 1.23 | 59 / 34 / 9% | 874 / 990 / 1009 mJ |
| Quench +0.5 / 1.0 / 1.5 µs, re-break 2.1 kV (R = 1) | 0.14 | 2.380 / 2.381 / 2.380 | 2.1 kV (clamped by re-break) | 1.85–1.88 kV | 77 | 1.31 | 48% | 476 mJ |
| Same, R 0.5 / 2 Ω | — | 2.373–2.383 | ≤2.1 kV | ≥1.85 kV | unchanged | unchanged | unchanged | unchanged |
| Quench, no re-break (all R, both breakdown cases) | — | **no fire within 13 µs** | **9.9–15.4 kV** | −6 to −11.5 kV (reversed) | — | — | — | 17–30 mJ (stage 1 only) |

- **Re-break timing:** re-break follows the quench by 18–37 ns with the eddy model, 6–37 ns with breakdown at the peak, and 5 ns with TTU.
- **Current after re-break:** the median is 1.5–1.8 A (eddy) and 15 A (TTU), with residual stage-1 ringing spikes of a few hundred A. That is the "early low-current re-break".
- **Re-break margin:** 4 kV ÷ 2.1 kV = 1.9×, as in the doc. In the re-break cases the node never needs more than 2.1 kV.
- **SRiso saturation:** SRiso saturates inside window B in every case where the channel conducts or re-breaks: 2.35–2.38 µs after breakdown (primary model) or 2.54–2.60 µs (TTU). The second, reverse-polarity half-cycle follows at about 6.3–10 µs, as the proposal describes.

**Temperature and flux margin.**
- Assumed derating: FINEMET FT-3 Bs is 1.23 T at 20 °C and 1.20 T at 100 °C (Hitachi/Proterial FINEMET catalogue, FT-3AM/FT-3SH table), with under 10% loss from 25 to 150 °C.
- That gives ≈1.19 T at 120 °C by interpolation, or about 1.13 T in the worst case (10% at 150 °C).
- With full bias reset, the available swing is 2.26–2.38 T at 120 °C against the 1.98 T design value: **14–20% flux margin**.

| Available swing | Delay |
|---|---|
| 1.98 T (design) | 2.37 µs |
| 2.26 T | 2.71 µs |
| 2.38 T | 2.86 µs |
| 2.46 T (20 °C) | 2.95 µs |

- The hot-to-cold delay drift is therefore about 0.1–0.25 µs.
- Delivery and peak current are essentially unchanged (76–77%, 1.30 kA).
- Peak H at 1.31 kA is about 36 kA/m, so the core sits about 0.045 T (μ0·H) above Bs. That is already inside the 0.27 µH saturated inductance.
- At 125 nF and 0.5 Ω, the peak is 2.06 kA (about 56 kA/m).

**Spike jitter (±20% of spike V·s).**
- On the simulated spike (0.14–0.18 mV·s): ±7–9 ns.
- On the doc's 1.2 mV·s: +61 / −60 ns, which matches the doc's estimate of about ±75 ns per ±0.3 mV·s.

**Other sensitivities (R = 1 Ω).**
- Eddy constant ×0.5 / ×2: delay 2.363 / 2.388 µs, delivery unchanged.
- SR1/SR2 Lu/Ls = 300: unchanged (delay 2.369 µs).
- SR3 Lsat 190 nH: edge about 3 ns, plug −51 kV, delay 2.365 µs.
- SR3 Lunsat 5 µH: see section 1, point 6. In the full chain the spike V·s rises to 0.48 mV·s and the core leakage to 2.7 mJ.

## 6. Mismatches with the hand calculations, and likely causes

1. **Delay 2.37 µs vs 2 µs.**
   - The doc budgets 1.5 mV·s for the spike. The simulated spike uses about 0.15 mV·s, because the full-voltage window is only 1–2 ns.
   - Separately, the 1.98 T design swing is pessimistic hot. Real FINEMET gives a longer delay (up to 2.9 µs).
   - The delay depends on the remaining V·s and is almost independent of R, so it can be set by design.
2. **Gap peak −51 kV vs −55 kV.**
   - The 1 nF C_block and Cw sit in series and parallel with the plug: ring-up is 1.69× instead of 1.74×.
   - Each lossless transfer also lands a little low: 33.5 → 32.9 kV.
   - **Getting the doc's 55 kV needs about +8% on stage 1** (for example, C0a charged to about 1.19 kV) or a smaller plug or Cw capacitance.
3. **Peak current at 2 Ω is 1.02 kA, not 0.9 kA.** The hand value is low. The exact series RLC gives 1.07 kA.
4. **Half-cycle 456 ns vs 408 ns, and Z0 +5%.** Saturation onset is not instantaneous: the core contributes inductance during its last ~0.05 T. With the TTU knee the effect is much larger (section 3).
5. **Stage-1 energy into the channel within the stage-1 window is only 20–34 mJ of 58 mJ.**
   - The rest stays in the lossless chain. At the end of the run, C_block holds about −6.0 to −6.8 kV instead of −4 kV (about 10–15 mJ), and C1–C3 still ring.
   - With the 10 MΩ × 1 nF = 10 ms bleed, C_block would not fully recover between shots at 150 Hz (6.7 ms).
   - This is a tentative finding: real SR losses and the energy-recovery path on C0a are not modelled.
6. **Spike leakage, C0b kick 1–1.3 V vs about 3 V.** The doc assumed the full 59 kV swing for a longer time. Losses split as Cw about 0.8–2.3 mJ and SRiso eddy current 0.3–1.0 mJ.

## 7. Limitations (read before trusting any number)

- **SR1–SR3** are lossless, single-valued saturable inductors, with no hysteresis, no eddy loss and no switching time. SR3 in particular is idealised as instructed. Its real behaviour (ferrite µr, switching delay, heating, 0.6 T hot swing; NiZn Bs is about 0.29 T at 100 °C, so ΔB of 0.6 T needs full ±Bs reset) decides whether a 2–5 ns edge exists at all.
- **Stage-1 ringing.** The post-pulse ringing in stage 1 (narrow node spikes during the delay) is undamped, so it is exaggerated.
- **SRiso core model** is the main uncertainty for energy delivery. Three of the four models agree that delivery matches the hand values: eddy, JA, and the doc's RLC. TTU as shipped (with its latch) predicts about 20 points less. The TTU equations were re-centred to represent bias reset, and that is my modification. The JA parameters are calibrated, not fitted, and the JA bias reset is incomplete.
- **Channel** is a constant resistance with a 1 ns switch. There is no burning voltage, no R(t), no physics for re-strike or extinction, and the 2.1 kV re-break threshold is the doc's rough ÷13 scaling. Whether a 2 A current keeps a channel alive is outside circuit simulation.
- **Not modelled:**
  - transmission-line, transit-time and parasitic effects in the plug cap and lead (lumped elements only)
  - parasitic L in the C0b loop beyond 0.03 µH
  - transformer saturation and leakage details
  - the bias circuits' coupling (except the Xyce bias winding)
  - temperature effects other than via ΔB
- **Xyce scope.** Xyce was run on the stage-2 block (SRiso + C0b + plug + channel), not the full chain.
- **Disk use.** Raw outputs are large and regenerable. `out/` was 3.5 GB in v1 and is about 6 GB after v2 pruning. The LTspice `.raw` files (5.2 GB) were deleted in v2.

## 8. What it means for the build

1. **Stage-2 delivery and SRiso sizing look sound.** About 77% / 1.3 kA at 1 Ω with 62.5 nF, and about 88% / 1.7 kA with 125 nF. Rate C0b and the switch path for at least 2.1 kA and 70% reversal (0.5 Ω, 62.5 nF), or 59% reversal at 125 nF.
2. **Re-think the delay accounting.** Re-budget SRiso to about 8.2–8.5 mV·s plus margin, or accept 2.4–2.9 µs. Either way, measure the hot ΔB of the actual core.
3. **Quench without re-break is the failure mode to design out.** Options worth evaluating before the build:
   - a resistive or diode clamp holding the node near 0 during the delay (for example, a high-voltage diode stack or a damping R from node to ground sized against the magnetising current)
   - a lower-resistance keep-alive path
   - or simply confirming on the bench that the channel re-breaks at about 2 kV within tens of ns

   Any clamp must not load the −51 kV spike, which needs checking in this model.
4. **SR3 is the gating component.** Bench-test a single-turn ferrite stack for unsaturated L of 50 µH or more at ns rates, and for hot ΔB, before relying on the 2–5 ns edge. Add about 8% to stage 1 if the full −55 kV at the gap is required.
5. **Measure a real SRiso core at kA and µs** (B–H under the stage-2 pulse). That is what settles the 58% vs 77–80% delivery question between the core models.

## 9. v2 follow-up: quench mitigation, SR3 as a real ferrite, C_block recovery (19 Oct 2026)

Driver: `run_v2.py` (or `run_all.py --v2-only`). It is resumable and checkpoints every case to `results/v2_checkpoint.jsonl`. All tables are in `results/v2_tables.md`. 447 cases ran; none failed after retries (finer `tmax` on "timestep too small"). Unless stated, the core model is the primary eddy model, R = 1 Ω, C0b = 62.5 nF, and breakdown is at 27.5 kV.

### 9.0 Headline

| Item | Result | Recommendation |
|---|---|---|
| 1. No re-break after quench | With no mitigation, the plug node rings to **+15.3 kV** (eddy) or **+32.4 kV** (TTU), about 1 µs after the quench. SRiso flux runs back to its reset point and the core reverse-saturates. If the channel then re-breaks at about 12 kV, stage 2 fires late and uncontrolled (+2.74 µs). | **Diode stack from the plug node to a stiff reservoir rail at about 4.4–5 kV** (just above the 4 kV bank). The node is limited to **5.4–6.0 kV in both core models**. Normal shots are unchanged (delivery 76.5% vs 76.6%). The only spike cost is the stack capacitance: gap peak −51.1 → **−50.1 kV** with 2 pF. In the no-re-break case stage 2 does **not** fire; it aborts safely and the bank keeps 476–486 mJ of 500 mJ. |
| 2. SR3 as NiZn ferrite | **No credible hot NiZn (4B1/4C65-class) SR3 at ≤ 190 nH holds off.** The plug follows C3 through the core's viscous (switching) impedance. Stage-1 block: 30–40 kV with a 25–45 ns 10–90% edge. **Full chain: −24 to −28.5 kV gap peak**, at or below the 27.5 kV breakdown. A single turn does not work at any geometry tried. | Needs higher µ **and** a lower switching coefficient than catalogue hot NiZn: µ ≥ about 1000–2000 and Sw ≤ about 5–10 A·µs/m at 8–12 turns (Lsat 105–155 nH). That gives −42 to −44 kV full chain and a 1.3–1.6 ns final edge, with a 2–4 kV pre-pulse. Measure Sw and hot µ on candidate cores (e.g. CMD10-class, Tc 250 °C) before committing. Otherwise re-plan the last stage (see 9.2). |
| 3. C_block recovery | With realistic (lossy) SR1/SR2, C_block ends each shot **1.4–1.8 kV more negative than −4 kV**. Between shots it rings in a high-Q tank (C1+C2+C3+C_block with the transformer magnetising L, about 4.5 kHz). With a low-loss transformer the residual **ratchets**: at 150 Hz, −4 → −10.4 kV after 8 shots, and the gap peak falls 40 → 31 kV. At 300 Hz it reaches −12.4 kV and shot 6 loses the spike. At 200/400/600 Hz it scatters by ±3 kV. | **Bleed resistor from the SR3 output (x) to ground, 100–300 kΩ** (60 kV pulse-rated, a few W). This replaces relying on the 10 MΩ C3 bleed. Residual is ≤ 0.01 kV (100 kΩ) or ≤ 0.2 kV (300 kΩ at 600 Hz) shot to shot, even with a lossless transformer. Gap peak is unchanged (−40.2 vs −40.3 kV). |

**A new caveat that matters more than any of the above.** Replacing the ideal SR1/SR2 with realistic nanocrystalline cores (eddy/viscous loss, ke = 4.5e-5 as for SRiso; N1 = 100, N2 = 40 turns) cuts the full-chain gap peak (no breakdown) from **−51.1 kV to −40.3 kV**. Pre-saturation leakage through SR1/SR2 and their switching loss cause this. The Rev B "−55 kV at the gap" therefore relies on low-leakage SR1/SR2 and SR3. With a real NiZn SR3 on top, the margin over the 27.5 kV breakdown is small or negative.

### 9.1 Item 1: no-re-break quench mitigations

**Setup**
- Quench at +1 µs after breakdown, with a 0.5 µs spot check.
- Re-break thresholds: 2.1 kV (hot), 6 kV, 12 kV, and none.
- "Normal" means no quench.
- Mitigation networks are added at the plug node through the new `extra_net` hook in `prs_model.netlist`.
- A diode stack is modelled as an ngspice diode with N = 6 and Rs = Ron, plus 2 pF stack capacitance (5 pF variant also run).
- The TTU behavioural core was run as a spot check.

**Mechanism found.** After the quench, the SRiso magnetising current (about 1.5–2 A) charges the plug capacitance. The node rises past the bank voltage, which drives SRiso backward. When the flux returns to the reset point the core reverse-saturates. SRiso then drops to its saturated 0.27 µH, and the bank and the stored magnetising energy ring the node:
- +15.3 kV (eddy), FWHM about 60 ns;
- +32.4 kV (TTU), FWHM about 13 ns.

This is the "node rises to 10–34 kV" result from v1, now explained. Any fix must either stop SRiso from being driven backward, or absorb the reverse-saturation ring with a low-impedance path just above 4 kV.

**Results** (eddy model; TTU in the last column; full table in `results/v2_tables.md`):

| Mitigation | Gap peak, no bd | Normal 1st half-cycle delivery | No re-break: node max | Stage 2 fires (no re-break) | Bank kept | Re-break only > 12 kV | TTU node max |
|---|---|---|---|---|---|---|---|
| none | −51.1 kV | 76.6% | **15.3 kV** | no | 489 mJ | late fire (+2.74 µs) | **32.4 kV** |
| (a) TVS/avalanche clamp to ground, X = 6 kV (Ron 20 Ω) | −50.1 | 76.5 | 9.7 | no | 487 | no | – |
| (a) TVS clamp to ground, X = 10 kV | −50.1 | 76.5 | 12.1 | no | 489 | late fire | 12.7 |
| (a) **Diode to a reservoir rail, 4.4 kV, 2 Ω** | **−50.1** | **76.5** | **5.4** | no (safe abort) | 476 | **no** | **5.4** |
| (a) Diode to a reservoir rail, 5.0 kV, 2 Ω | −50.1 | 76.5 | 5.9 | no | 483 | no | 6.0 |
| (a) Diode to a reservoir rail, 4.4 kV, 10 Ω | −50.1 | 76.5 | 7.7 | no | 478 | no | – |
| (c) Diode across SRiso (node → bank), 2 Ω | −50.1 | **61.9** (freewheels the bank reversal; 187 mJ in the diode) | 5.0 | no | 489 | no | – |
| (c) Diode across SRiso + 300 Ω / 1 kΩ | −50.1 | 76.3 / 76.5 (total channel energy 83 / 89%) | 14.1 / 14.8 | no | 490 | late fire | 15.4 / 12.7 |
| (b) AC hold-down R–L–C to ground (100 Ω, 2–10 nF, 10–100 µH; 9 combinations + R 30/300 Ω + RC) | −50.9 to −51.1 | 75.8–77.4 | 12.5–22 (worse) | SRiso saturates on time in some cases, but the bank dumps into the hold-down, not the gap | 401–474 | it acts as a re-strike kick | 20.0 |
| (b) Timed crowbar, 2 Ω at +3 µs | −51.1 | 76.6 | 15.3 (before it fires) | bank dumped into the crowbar (460 mJ) | 23 | – | – |
| (b) SRiso forward kick winding, 15 A for 300 ns at +2 µs | −51.1 | 76.6 | **38.1** | SRiso forced to saturate; no gap delivery | 490 | – | – |

**Findings**
- **A DC resistive bleed at the node is not viable.** The node rests at +4 kV, so any resistor to ground carries DC through SRiso. A bleed strong enough to matter against about 2 A magnetising current (≤ about 2 kΩ) would dissipate about 8 kW. A tolerable one (≥ 10 MΩ, 1.6 W) does nothing. This is a calculation; it was not simulated.
- **A clamp to ground must sit above 4 kV.** It therefore cannot hold the node "near 0". It can only absorb the reverse-saturation ring, and it needs a low dynamic impedance to do so: peak clamp current is about 500 A for about 100 ns.
  - A TVS stack (Ron about 20 Ω) only reaches 9.7 kV at X = 6 kV.
  - A diode stack into a capacitor-backed rail reaches 5.4 kV.
  - Neither touches normal operation, because during stage 2 the node stays below about 1.3 kV.
  - The only spike cost is the stack capacitance (1 kV of gap peak per 2 pF).
- **Diode across SRiso** works for the quench (5.0 kV), but it freewheels the normal bank reversal: delivery 76.6 → 61.9%, and 187 mJ per shot in the diode. Adding series R removes the delivery hit but also the protection. Rejected.
- **AC hold-down (b)** keeps SRiso firing on schedule, but it does not help:
  - C_h discharges into the channel at breakdown;
  - at the quench, the L_h current kicks the node to 12–22 kV;
  - the bank then dumps into C_h/R_h (35–85 mJ), not the gap.
  - Rejected.
- **No passive network can make stage 2 deliver into a channel that will not re-break.** Re-strike assist means generating more voltage at the node. The kick winding does that (38 kV), but it is an uncontrolled second spike, and the hold-down did it by accident.
  - The defensible goal is therefore a **safe abort**: node limited, no late uncontrolled fire, bank energy kept for the next shot. Bias resets SRiso between shots.
  - The reservoir-rail clamp achieves this in both core models.
- **Recommended: the 4.4–5 kV reservoir clamp.**
  - Diode stack: about 65 kV PIV, pulse-rated for about 0.5 kA / 100 ns, about 2 pF.
  - Rail capacitor: ≥ 1 µF, so that about 3 µC (eddy) to about 30 µC (TTU) per aborted shot raises it by ≤ 30 V.
  - The rail is held about 0.4–1 kV above the bank by the charger, e.g. a tap or a shunt regulator back to the C0b supply.
  - Gap peak: −50.1 kV, which is **below 51 kV in magnitude by 1.0 kV** (2%); about 2.4 kV at 5 pF.
  - Normal-shot delivery is unchanged.
  - Untested: diode reverse recovery after an abort, and rail regulation.

### 9.2 Item 2: SR3 as a NiZn ferrite coaxial switch

**Model** (`prs_model.vcore`; a generic saturable core, also used for SR1/SR2 in item 3). The winding current is

I = (le/N)·[Hc·tanh(Ḃ/ε) + ke·Ḃ + B/(µ0·µΔ)] + saturation walls.

- B is the forward flux density from the bias-reset point.
- The forward wall is at N·A·ΔB_hot. The reverse wall sits just below 0, because the core is reset to −Bs by bias.
- After saturation the switch is L_air = N²·2e-7·len·ln(b/a) + 5 nH lead (ASSUMED), with b = OD/2 + 8 mm (HV clearance to the return can) and a = ID/2 − 2 mm.
- **Rate effect.** It uses the ferrite switching-coefficient law (H − H0)·τ = Sw, i.e. ke = Sw/ΔB. Sw = 20 A·µs/m (0.25 Oe·µs), from NBS TN-90 (Ni–Zn about 0.25 Oe·µs). This is consistent with the KEK/CAT report that NiZn needs about 3 Oe to switch in 100 ns. Sweep: 5–40 A·µs/m.
- Eddy currents are negligible in NiZn (ρ ≈ 1e5 Ω·m for 4B1/4C65, 1e8 Ω·m for CMD5005); the viscous term covers the domain-wall/rotation damping.
- Not modelled: gyromagnetic switching below about 5 ns, and dimensional resonance.

**Materials (hot, about 100 °C)**

| Material | Bs @ 25 / 100 °C | ΔB used (bias reset, hot) | µΔ used | Hc used | Tc | Source |
|---|---|---|---|---|---|---|
| Ferroxcube **4B1** | 360 / 310 mT | 0.55 T | 250 | 100 A/m (ASSUMED from loop) | ≥ 250 °C | [4B1 data sheet](https://elnamagnetics.com/wp-content/uploads/library/Ferroxcube-Materials/4B1_Material_Specification.pdf) |
| Ferroxcube **4C65** | 380 / 340 mT | 0.60 T | 125 | 200 A/m (ASSUMED) | ≥ 350 °C | [4C65 data sheet](https://download.ferrite.de/pdf/4c65.pdf) |
| **CMD5005** (25 °C only) | 330 mT; Br 130 mT | 0.60 T | 2100 | 9.5 A/m (0.12 Oe) | **130 °C, unusable hot** | [CMD5005 data sheet](https://magneticsgroup.com/wp-content/uploads/2019/09/CMD5005-ISO-WEB-DATA.pdf) |
| Hypothetical "fast high-µ NiZn" | 4C65 swing | 0.60 T | 500–5000 | 50 A/m | – | Requirement study. The nearest real candidates are National Magnetics CMD10 (µi 625, 430 mT, Tc 250 °C, marketed for pulsed power) and CN20 (µi 925, Tc 185 °C) ([NMG NiZn table](https://www.magneticsgroup.com/material/nickel-zinc-ferrite/)). |

**Geometry rule.** The iron area is set so that N·A·ΔB = fvs × 0.68 mV·s (fvs 1.0 or 1.5). The stack length is A/((OD−ID)/2). Grid:
- 4B1 and 4C65: N = 1–4 at ID/OD 25/60, 25/80 and 15/40 mm, and N = 6–16 at 25/80.
- CMD5005: N = 1–16.
- Sw: 10 / 20 / 40.
- Hypothetical µ: 500–5000 with Sw 5–20.

That is 116 stage-1-block runs plus 8 full-chain runs.

**Results**

| Design | Lsat | Stack | Stage-1 block plug peak | 10–90% / 50–90% edge | Plug V when SR3 saturates | Full-chain gap peak |
|---|---|---|---|---|---|---|
| Ideal SR3 (v1) | 10 nH | – | −55.9 kV | 0.74 ns / about 0.5 ns | – | −51.1 kV |
| Ideal SR3 (v1) | 190 nH | – | −55.6 kV | 3.1 ns (10–90%), 4.8 ns to 98% | – | – |
| 4C65 / 4B1, **1 turn**, any ID/OD | 18–53 nH | 41–148 mm | **−30.5 kV** | 25.7 / 12 ns | never saturates | – |
| 4C65, 4 turns, 25/80, 10 mm | 55 nH | – | −30.7 | 25 / 10 | never | −24.4 kV |
| 4C65, 12 turns, 25/80, 3.4 mm | 155 nH | – | −38.3 | 32 / 15 | never | −28.0 kV |
| 4C65, 16 turns | 205 nH | – | −40.2 | 35 / 16.5 | never | −28.5 kV |
| 4B1, 12 turns | 169 nH | – | −38.4 | 40 / 20 | never | −25.7 kV |
| CMD5005, 16 turns (25 °C only) | 205 nH | – | −41.0 | 30 / **2.6** | −15.6 kV | −39.7 kV |
| Hypothetical µ 2000, Sw 5, 12 turns | 155 nH | – | −47.0 | 18 / 1.7 | −9.5 kV | **−44.1 kV** |
| Hypothetical µ 5000, Sw 10, 12 turns | 155 nH | – | −44.6 | 25 / 1.9 | −12 kV | −42.4 kV |

**Why a single turn cannot work (analytic check, consistent with the sweep).** During the 40 ns C3 charge, the core draws a leakage current I = le·H/N. H is the static loop term B/(µ0·µΔ) (about 3800 A/m at full swing for 4C65) plus the switching term Sw/T (about 500 A/m). The hold-off fixes N·A, and the saturated inductance grows as N²·len. Together these give a turns-independent bound:

I_leak · Lsat ≥ (µ0/2π) · H · (VS/ΔB) · (le/hw) · ln(b/a)

- For 4C65 at 25/80 mm this is about 5e-6 A·H. At 190 nH that means I_leak ≥ about 25 A.
- But the plug (16.5 pF to −50 kV in 40 ns) only needs about 20 A in total.
- So the plug is charged through the "unsaturated" core and simply follows C3 (C3 itself is pulled down to about −30 kV).
- Adding turns or area cannot escape the bound. Only higher µΔ, lower Sw, a longer C3 charge with a high-µ material, a larger Lsat budget, or a smaller le/hw ratio helps.
- **Bias is mandatory**: unbiased swing is Bs − Br, about 0.2 T. It is also heavy: H_bias ≈ ΔB/2/(µ0µΔ) + Hc means about 210 A·turns (4B1), about 400 A·turns (4C65) and about 70 A·turns (CMD5005) on a 25/80 mm core.

**Recommendation for SR3**
1. Do not build Rev B around a single-turn hot NiZn SR3.
2. Shortlist pulse ferrites with µi ≥ 600–1000 and Tc ≥ 200 °C (e.g. CMD10-class). Measure Sw and µΔ at 100 °C on a 40 ns, 0.6 T test pulse. The sweep says Sw ≤ about 5–10 A·µs/m and µΔ ≥ about 1000–2000 are needed for −42 to −44 kV and a 1.5–2 ns final edge, at 8–12 turns, Lsat 105–155 nH, 25/80 mm, 3–5 mm stack.
3. If that cannot be met, re-plan the last stage: e.g. accept a 15–25 ns edge, or move the sharpening onto a different element. A design study is needed; it was not simulated here.

### 9.3 Item 3: C_block recovery between shots

**Shot model**
- Full chain with **lossy SR1/SR2**: `vcore` nanocrystalline, ΔB 2.0 T hot, Hc 2.5 A/m, ke 4.5e-5, µΔ 5e4, N1 = 100, N2 = 40.
- Lsat 81 µH / 3.2 µH as in the document.
- Ideal SR3 at 10 nH (the ferrite SR3 is unresolved, item 2).
- Eddy SRiso, breakdown at 27.5 kV, R = 1 Ω.
- Initial states (C1–C3, C_block, L_sec current) are carried from shot to shot.

**Inter-shot model** (linear, `run_v2.recovery`):
- SR1–SR3 held by bias in reverse saturation, i.e. their saturated L with 1 Ω.
- Plug side held at +4 kV by the recharged bank.
- Transformer secondary = magnetising L (0.96 H, from the assumed 1 mH primary), R_w 20 Ω, and a core-loss shunt R_c of ∞ / 1 MΩ / 200 kΩ (Q about ∞ / 37 / 7).
- C3 bleed 10 MΩ.
- Optional R_x from the SR3 output (x) to ground.
- Bias reset of the cores is assumed complete. C0a and C0b are recharged to 1.1 / 4.0 kV each shot.

**Results**

| Inter-shot network | 150 Hz (8 shots) | 200 Hz burst | 300 Hz burst | 400 Hz burst | 600 Hz burst |
|---|---|---|---|---|---|
| Lossless transformer (10 MΩ bleed only) | **−4 → −10.5 kV**, gap 40 → 31 kV | −1.3 to −3.0 kV (scatter) | **−4 → −13.1 kV; shot 6 loses the spike** | −0.3 to −2.9 kV | −0.8 to −3.3 kV |
| R_c 1 MΩ (Q ≈ 37) | −4.21 kV | −3.63 | −5.05 | −3.28 | −2.79 |
| R_c 200 kΩ (Q ≈ 7) | −4.00 | −4.00 | −4.01 | −3.99 | −3.86 |
| R_c 1 MΩ + R_x 1 MΩ | −4.02 | −3.94 | −4.25 | −3.79 | −3.26 |
| R_c 1 MΩ + **R_x 300 kΩ** | −4.00 | −4.00 | −4.01 | −3.99 | −3.81 |
| R_c 1 MΩ + **R_x 100 kΩ** | −4.00 | −4.00 | −4.00 | −4.00 | −4.00 |
| Lossless transformer + **R_x 100 kΩ** | −4.00 | −4.00 | −4.00 | −4.00 | −3.99 |

(Steady-state C_block voltage at shot start, ideal −4.00 kV. Per-shot sequences are in `results/v2_tables.md`.)

- At the end of every shot C_block sits at −5.4 to −5.9 kV, i.e. 1.4–1.8 kV of excess. That excess is stage-1 energy left in C1–C3 and C_block. The v1 lossless figure was −6.0 to −6.8 kV.
- Between shots, this excess rings in a 4.5 kHz tank: C1+C2+C3+C_block (about 1.3 nF) with the transformer magnetising inductance. The 10 MΩ bleed (τ ≈ 26 ms) barely damps it.
- Whether the residual decays, scatters or ratchets depends on the transformer's small-signal loss and on the phase at the next trigger. Neither is known.
- **Fix: R_x = 100–300 kΩ from the SR3 output node (x) to ground.**
  - The node sits at 0 V between shots, so there is no standing loss.
  - It dissipates 1.7 mJ (300 kΩ) to 4.8 mJ (100 kΩ) during the shot window, mostly the residual that must be removed anyway. That is about 0.5–3 W at 150–600 Hz.
  - Gap peak is unchanged (−40.2 vs −40.3 kV); delivery and delay are unchanged (76.7%, 2.369 µs).
  - 100 kΩ gives zero residual even with a lossless transformer. 300 kΩ leaves ≤ 0.2 kV at 600 Hz.
  - It must hold 60 kV pulses: a resistor string with voltage grading.

### 9.4 Mismatches and caveats (v2)

- **The lossy SR1/SR2 parameters are assumed.** The turns, ke, µΔ and a geometric Lsat well inside the document's 81 µH / 3.2 µH were not designed in detail. The −40 kV realistic gap peak is indicative only, but a 10–20% loss of spike amplitude relative to the ideal chain should be expected.
- **The ferrite Sw comes from the literature** (0.25 Oe·µs, a domain-wall regime figure at about 100 ns), not measured on 4B1, 4C65 or CMD10 at 100 °C. All item-2 conclusions hinge on Sw and µΔ. The hypothetical-material rows show what to measure. Gyromagnetic switching (< 5 ns), DC-bias effects on µΔ and dimensional resonance are not modelled.
- The **SR3 Lsat formula** is an ideal coaxial/toroidal estimate. Real multi-turn windings will have more leakage L, which is pessimistic for the 12–16-turn designs.
- **Item 1 depends on the reverse-saturation model of SRiso**: the reset point equals the wall. If the real core has a softer reverse knee, the ring after quench will be smaller (eddy) or of TTU size. The reservoir clamp handles both.
- **Item 3 assumes complete bias reset** and an ideal 10 nH SR3. The tank frequency (4.5 kHz) depends on the assumed 1 mH primary magnetising L. Transformer core loss (Q) is unknown, which is why a resistor is recommended rather than relying on it.
- The **0.5 µs-quench rows for some mitigations were not run**, because the grid was trimmed. The 1 µs rows are the reference.
- **Raw outputs were pruned** to keep the disk tidy: v2 waveforms not used in plots, and the LTspice `.raw` files (5.2 GB). Everything is regenerable from the checkpoint and the scripts. `out/` is now 6 GB.

### 9.5 Plots (v2)

- `plots/09_quench_mitigations.png`: node waveforms with no re-break (eddy and TTU), and node max vs normal delivery for each mitigation.
- `plots/10_sr3_ferrite.png`: plug peak and final edge vs SR3 Lsat for all materials and turns, plus stage-1 waveforms.
- `plots/11_cblock_multishot.png`: C_block voltage at shot start and gap peak per shot, for 150 Hz and 200/300/400/600 Hz bursts and every inter-shot network.
- `plots/12_cblock_recovery_waveforms.png`: the 4.5 kHz inter-shot ringing, with and without R_x.

## Files

- Scripts: `run_all.py`, `prs_model.py`, `analysis.py`, `ltspice_run.py`, `xyce_ja.py`, `run_v2.py` (v2 follow-up; `run_all.py --v2` / `--v2-only`)
- TTU model: `ttu/` (original zip and `Core_Model_recentred.sub`)
- Build script: `xyce/build_xyce.sh`
- Results: `results/results.json`, `results/results.csv`, `results/tables.md`, `results/xyce_ja.json`; v2: `results/v2_checkpoint.jsonl`, `results/v2_tables.md`
- Plots (`plots/`):
  - `01_stage1_validation.png`
  - `02_stage2_block_validation.png`
  - `03_fullchain_node_and_SRiso_delay.png`
  - `04_fullchain_stage2_current_bank.png`
  - `05_quench_cases.png`
  - `06_core_model_comparison.png`
  - `07_summary_delivery_delay.png`
  - `08_jitter_and_flux_swing.png`
  - v2: `09_quench_mitigations.png`, `10_sr3_ferrite.png`, `11_cblock_multishot.png`, `12_cblock_recovery_waveforms.png`
