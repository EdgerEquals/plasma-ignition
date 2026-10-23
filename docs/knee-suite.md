# Knee Suite (13 knees)

*Stratified Sphere / Stratified Core Refrigerator. Updated 23 Oct 2026 (AWST). This replaces the Drive doc "Knee Suite (12 knees) 2026-10-18". Nothing here has been measured: every value is a literature figure, a calculation or an assertion from the design record.*

## What a knee is

A **knee** is a threshold or switch point where a domain's energy behaviour changes sharply: a natural switch point for energy discharge in a resonant system. The working rule since 18 Oct is "rungs store, knees mix". Storage modes (rungs) stay linear and high-Q, and each knee is a small nonlinear region that couples two modes, so energy hands off between domains instead of being lost as heat.

## The 13 knees

| # | Knee | Value / threshold | Domain | Source |
|---|---|---|---|---|
| 1 | Gd magnetocaloric effect at the Curie point | Gd Curie ~293–300 K (~20 °C); 6.75 kHz drive at ~0.2 T | Thermal | Grok design thread [1922], 18 Oct; Knee Suite 2026-10-18 #1 |
| 2 | Domain-wall resonance | ~200 kHz (216 kHz sideband or harmonic 8 at 204 kHz) | Magnetic | Grok thread [1424], [1922], 17–18 Oct; recorded as replaced by #11 |
| 3 | Shell and cavity breathing | Shell 20–500 kHz; HHO cavity 13 kHz to a few hundred kHz; 1.5 mm bubble 433 kHz (calculated, not measured) | Acoustic | Grok thread [1426], [1922]; Knee Suite #3 |
| 4 | LC tanks (BN joints, later one BST tank) | 950–1900 kHz, then a 6.75–830 kHz φ ladder | Electrical | Grok thread [1424], [1686]; Living Spec v2 (18 Oct) |
| 5 | Ortho-para H₂ conversion | 340 J/mol (a ~77 K figure); flat above ~200 K | Chemical | Grok thread [1208], [1922]; dormant |
| 6 | Balmer lines | 457–691 THz (Hα 656, Hβ 486, Hγ 434 nm) | Optical | Grok thread [1426], [1430] |
| 7 | Plasma frequency (the "moving knee") | 900 MHz → 13 THz claimed; recalculated at ≤ ~9–52 GHz for the fill | None given (bridge) | Grok thread [1568], [1716]; Knee Suite #7 |
| 8 | Ignition spark (arc flash at the diamond boundary) | Paschen minimum ~290 V at 1.2 Torr·cm; ignition ~850 K, designed never to be reached | None given (bridge) | Grok thread [1714], [1953] |
| 9 | Atom-count ceiling (full ionisation) | ~13 THz claimed, corrected to ~13 GHz; now retired | None given (ceiling) | Grok thread [1728]–[1732], [1975] |
| 10 | H₂ vibrational intermediate | ~125 THz (124.6 THz Raman, 2.4 µm) | None given (bridge) | Grok thread [1736], [1922] |
| 11 | Saturation bend | B–H curvature in NiZn or carbonyl iron (Fair-Rite 61: ~250 mT at 1200 A/m) | Magnetic | Claude, "Mode and Knee List" 2026-10-18; Grok thread [1977] |
| 12 | Magnetoelastic ΔE effect | Stiffness of Ni or Galfenol changes with field bias (ΔE/E up to ~160 %) | Magnetic → acoustic | "Mode and Knee List" 2026-10-18; candidate |
| 13 | **Pair production** (new, 23 Oct 2026) | **1.022 MeV = 2mₑc²** near a nucleus (≈2.47×10²⁰ Hz, λ ≈ 1.21 pm); **2.044 MeV** near an electron | Not yet assigned (see Open questions) | Added 23 Oct 2026. Above this threshold a gamma photon can convert into an electron–positron pair |

At the end of the 18 Oct review (Grok thread [1977]–[1978]) only #11 switched stored energy, #1 dumped heat only, and #12 was a candidate. #3–#10 were marked as non-starters for the 18 Oct design.

## Energy domains

The six energy domains (Grok thread [1922], 18 Oct; "Mode and Knee List" 2026-10-18):

1. Thermal
2. Magnetic
3. Acoustic
4. Electrical
5. Chemical
6. Optical

The seventh is the **information layer**, added 19 Oct 2026 ("Stratified Sphere — Information Layer (Harness Architecture) 2026-10-19"). It treats the flow of information through the harness stack as its own domain on top of the six.

Note: the 17 Oct "Six-Delta Architecture" doc listed *mechanical* where later lists have *magnetic*.

## Named elsewhere (not counted in the 13)

- **Ionisation knee:** about 10 Torr for a 1 mm gap (p·d ≈ 1 Torr·cm). Named in the 19 Oct design notes as the correct term in place of "plasma knee".
- **Lamb knee:** ~1057 MHz. Named on 17 Oct and later dropped.
- **Knee Suite 2026-10-18 candidates C1–C6:**
  - Curie permeability roll-off in Fe, Ni and ferrite
  - ferromagnetic resonance (28 MHz–3 GHz)
  - Pd hydride α–β phase change
  - the ionisation/recombination clock
  - graded Gd–Tb Curie points
  - the Ni magnetostriction thermal valve
- **base5 knee table (draft, 21 Oct):**
  - smoky-quartz bleaching (473 K)
  - χ² frequency-shift knee (PPLN/KDP)
  - piezo knee (BTO, ~28.9 MV/m field scale)
  - quartz α–β inversion (573 °C)
  - BTO Curie point (393 K)
  - BTO field-tuned capacitance
  - ferrite Curie point (> 573 K)
  - Gd-Dy Curie knee (~260 K)
  - CALORIVAC transition (261–310 K)
  - HHO autoignition (773–858 K)
  - H₂ dissociation (4.478 eV)
- **19 Oct design notes:**
  - dielectric knee (BTO)
  - mechanical stress knee (48 MPa quartz)
  - phosphor absorption edge or saturation knee

## Open questions

1. **#11 vs #2.** The record says the saturation bend (#11) *replaced* domain-wall resonance (#2). It wasn't added alongside it. If that holds, one slot opens. The ionisation knee (about 10 Torr at a 1 mm gap, from the 19 Oct notes) is the candidate to fill it.
2. **Which base list?** Should the 17-knee base5 table from 21 Oct replace the 12-knee base used here?
3. **Domain for pair production (#13).** It converts electromagnetic radiation (the top of the optical/EM range) into rest mass. That fits none of the seven domains cleanly. Options are optical, or a new particle/nuclear domain.
4. **Unassigned bridges.** #7–#10 have no domain. The information layer has no knee.
