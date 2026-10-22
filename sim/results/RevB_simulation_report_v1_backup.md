# Plasma Ignition Rev B: circuit simulation report

Danny's working file, 18 Oct 2026. Not for Vikas, and not sent. Every number below comes from a simulation run on the box, or from the Rev B proposal (`../PRS_RevB_architecture_proposal.md`) where it is labelled "hand". The simulations are lumped-element models with assumed core models. They are not measurements.

## 1. Bottom line

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
- **Disk use.** Raw outputs are large: `out/` is 3.5 GB and `ltspice/runs` is 5.2 GB. Both can be deleted and regenerated.

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

## Files

- Scripts: `run_all.py`, `prs_model.py`, `analysis.py`, `ltspice_run.py`, `xyce_ja.py`
- TTU model: `ttu/` (original zip and `Core_Model_recentred.sub`)
- Build script: `xyce/build_xyce.sh`
- Results: `results/results.json`, `results/results.csv`, `results/tables.md`, `results/xyce_ja.json`
- Plots (`plots/`):
  - `01_stage1_validation.png`
  - `02_stage2_block_validation.png`
  - `03_fullchain_node_and_SRiso_delay.png`
  - `04_fullchain_stage2_current_bank.png`
  - `05_quench_cases.png`
  - `06_core_model_comparison.png`
  - `07_summary_delivery_delay.png`
  - `08_jitter_and_flux_swing.png`
