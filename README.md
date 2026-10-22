# Plasma Ignition: Rev B simulation

Circuit simulation and design review for the Rev B architecture of the Plasma Ignition project, a two-stage plasma ignition system for HHO engines.

- **Stage 1** is a high-voltage breakdown spike. A low-voltage bank and step-up transformer feed a magnetic pulse compression chain of saturable reactors (SR1, SR2, SR3), which delivers a fast, ns-scale edge to the plug.
- **Stage 2** is an energy-delivery bank. It fires into the hot channel about 2 µs after breakdown, through the isolating saturable reactor SRiso and a DC-blocking capacitor.

The work is first-pass engineering analysis. The numbers are simulation results and hand estimates, not measurements.

## What is modelled

- **Magnetic pulse compression.** SR1 and SR2 are nanocrystalline saturable reactors, modelled both as ideal saturating inductors and as lossy real cores. Volt-second budgets and bias reset are included.
- **SR3.** A single-turn coaxial NiZn ferrite reactor in the plug cap, modelled as an ideal saturating inductor and as real ferrite. Includes turn-count and permeability sizing.
- **SRiso isolating reactor.** Its saturation timing sets the stage-2 delay. The study covers flux margin at 120 °C and ±20% spike jitter.
- **Channel.** A switch closes at breakdown into 0.5–2 Ω, with an optional quench mid-delay. The results report delivered energy, peak current, capacitor reversal and spike leakage into the bank.
- **Quench mitigation.** Clamp and fallback options for a quench where the channel does not re-break.
- **DC-block recovery.** Shot-to-shot charge build-up on the DC-block capacitor at 150 Hz and in 200–600 Hz bursts, and the bleed resistor that fixes it.

The full write-up, with the validation table, method, results and limitations, is in [`sim/RevB_simulation_report.md`](sim/RevB_simulation_report.md). The design numbers are in [`PRS_RevB_architecture_proposal.md`](PRS_RevB_architecture_proposal.md).

## Tools

- **ngspice + Python** is the primary engine. It builds netlists, runs batches and post-processes the results.
- **LTspice under Wine** is a cross-check of SRiso using the Texas Tech University (TTU) behavioural nanocrystalline core model.
- **Xyce** is a tie-break using its built-in Jiles–Atherton core model.

## Running

```bash
cd sim
python run_all.py            # base Rev B study (validation, sweeps, quench, jitter, plots)
python run_all.py --no-lt --no-xyce   # ngspice only
python run_v2.py             # follow-up: quench mitigation, SR3 ferrite, DC-block recovery
python run_v2.py --items 2   # run a single follow-up item
```

### Dependencies

- Python 3 with `numpy` and `matplotlib`.
- `ngspice` on `PATH`.
- Optional, for the LTspice cross-check:
  - Wine and the LTspice Windows build, unpacked to `sim/ltspice/app/LTspice/` (not included).
  - The TTU core model, which is not redistributed here. Download it from https://www.p3e.ttu.edu/BehavioralMagneticCoreLTspice and save `Core_Model.sub` as `sim/ttu/Core_Model_recentred.sub`, applying the B-axis re-centring described in the report. A Python port of the model's equations for ngspice is in `prs_model.py` (`model="ttu"`).
- Optional, for the tie-break: Xyce, built to `sim/xyce/install/bin/Xyce` (not included).

## Layout

```
PRS_RevB_architecture_proposal.md   Rev B design numbers (hand calculations)
GAP3SLT33-214_footprint_check_*.md  component footprint check
sim/
  prs_model.py      netlist builders, core models, ngspice runner
  analysis.py       metric extraction
  run_all.py        base study driver
  run_v2.py         follow-up study driver
  ltspice_run.py    LTspice (Wine) batch runner
  xyce_ja.py        Xyce Jiles–Atherton tie-break
  RevB_simulation_report.md
  netlists/         generated netlists from the committed runs
  ltspice/runs/     LTspice cross-check netlists and logs
  plots/            figures used in the report
  results/          tables, CSV/JSON results, checkpoints, run logs
```

Raw waveforms (`*.raw`) and the scratch output directory `sim/out/` are regenerated on each run and are not committed. The committed netlists, results and plots are a snapshot of the runs behind the report.
