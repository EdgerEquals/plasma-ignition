# Rev C reply

Working document. Not for external distribution.

## Voice channel

**a)** No. This session cannot join the Plasma Ignition Bot call or push audio into it. The Voice connector only makes a speech file. It does not enter that call.

**b)** Best path that already works: a Google Doc in the Plasma Reignition System folder, which the bot can open.

- Note: [Rev C – Design-out by margin](https://docs.google.com/document/d/1WS7AtAvDO1bfp29siYSn66MdV2HteqHdhHPztMZCBhE/edit)
- Plots in the same folder: SR3 edge, SRiso energy, re-strike node.

GitHub is the right home for `sim/run_revc.py`. This reply is the push. No email connector and no webhook were available.

**c)** Chat still works. This file is that reply.

## Result

Rev B topology held. Every move past 5% is flagged. This reply and `sim/RevC_design_out_by_margin.md` are the source of truth. `sim/results/revc/revc_summary.json` still has an abandoned auto-size (38.6 nF). Do not quote that. The chosen bank is 63.2 nF.

| Unknown | Chosen size | Worst margin | Best margin | Kind |
|---|---|---|---|---|
| SR3, hot ferrite | 26 turns, 25×60 mm, stack 4.1 mm, Lsat 714 nH, bias 359 A-t | Does **not** saturate. Gap **−25.8 kV**, 10–90% **45 ns** | Still does not saturate. Gap **−26.5 kV**, 10–90% **56 ns** | SIMULATED |
| SRiso | 5.63 kV, 63.2 nF, **1.0 J**, N=6, Ae 10.6 cm², 12.75 mV·s | TTU first half **575 mJ**, **+47%** on 390 mJ | Eddy **708 mJ**, **+82%**. JA not re-run | SIMULATED, except JA |
| Re-strike ~2 µs | Bank 5.63 kV = 1.5× the 3.75 kV worst end. No clamp | Re-breaks. Voltage margin 1.50× | Re-breaks. Margin ~5.8× on 0.98 kV | Voltage HAND. Re-break SIMULATED |

**SR3 does not close.** Worst-case 4C65-class NiZn (µ 100, Sw 40 A·µs/m, ΔB 0.55 T, 120 °C) can be sized to the leakage bound (49 A at 190 nH on the 25×80 reference, matching the corrected ~47 A) and still never hits the knee. **FLAG:** turns 1→26, Lsat 10 nH→714 nH, volt-seconds 0.68→1.02 mV·s. With lossy SR1/SR2 the gap is **−22.4 kV**. Sensitivity only, not adopted: µ 1000–2000 and Sw 5–10 A·µs/m does saturate (gap −40.6 / −45.3 kV, 10–90% 20 ns / 4.4 ns).

**SRiso.** "Enough" is the Rev B hand table: 78% of 0.5 J in the first half-cycle = **390 mJ**. Unmodified Rev B: eddy 76.7% / 371 mJ, TTU **61.4% / 291 mJ**. **FLAG:** TTU vs the report's 58%, not tuned. Raising voltage at fixed 0.5 J makes TTU worse (202 mJ). The 1 J ceiling restores it. **FLAG:** V +41%, energy +100%, VSiso +34%, Ae +33%, Lsat +33%. C0b 62.5→63.2 nF is only +1.1% and is a coincidence, not "unchanged." Film rating **≥ 9 kV**, 100% reversal (reverse peak about −2.9 kV). JA/Xyce was not available.

**Re-strike, HAND bracket, not a measurement.** GX120 at 25° BTDC, 0.75 mm: cold break 14.4 kV. Hot channel at ~2 µs: 0.98 / 1.95 / **3.75 kV**. Rev B's 4 kV is only 1.07× the worst end. In the eddy quench (no clamp) 4 kV does re-break, including at 3.75 kV, with 7% in hand. 5.63 kV re-breaks at 2.27 µs, reversal 52%, 1.71 kA. SRiso delay stays ~2 µs because the volt-second budget was rescaled with voltage.

Baseline before any resize matched Rev B within 1% (ideal plug −55.84 kV, ideal gap −50.92 kV, lossy SR1/SR2 gap −40.12 kV). **HAND, not re-simulated:** +8% on stage 1 does not restore −55 kV; the ratio from −40.1 kV is about +37%.

One measurement each: a 40 ns / 0.5 T pulse on the SR3 candidate at 120 °C (µ and Sw); one kiloamp pulse on the real SRiso core; one double-pulse at ~9 atm in the real mix. Until the first of those, SR3 stays a ~45 ns pass-through and the −55 kV edge is not available.

Full note, tables, and file list: `sim/RevC_design_out_by_margin.md`.
Study script: `sim/run_revc.py`.
Plots: `sim/plots/revc/`.
