# GAP3SLT33-214 (SMB / DO-214AA) footprint check - 16 Oct 2026

Source: GeneSiC GAP3SLT33-214 datasheet Rev 1.4 (Apr 2020), page 5, "Recommended Solder Pad Layout" (inch controls).
Copy at /tmp/gap214b.pdf (from https://pdf.htelec.com/pdf/3/GAP3SLT33-214.pdf).

Datasheet recommended pads:
- Pad length along diode axis: 0.085" (2.16 mm) min, each pad
- Gap between pads: 0.107" (2.74 mm) max
- Pad width across axis: 0.089" (2.26 mm) max
- Package: body 4.06-4.57 mm, overall lead span 5.21-5.59 mm, cathode band = K

KiCad stock Diode_SMD:D_SMB (kicad-footprints master):
- Pads 2.5 x 2.3 mm at x = +/-2.15 mm -> pad gap 1.80 mm, outer span 6.80 mm

Comparison:
- Pad length 2.50 vs >=2.16 mm: OK
- Pad width 2.30 vs <=2.26 mm: 0.04 mm over (marginal, cosmetic)
- Pad gap 1.80 vs 2.74 mm: stock gap is 0.94 mm narrower than GeneSiC's layout. Technically inside the "max", but for a 3.3 kV part sitting on the ~2.6 kV node this throws away surface creepage.

Recommendation (check note, not a locked change):
- Use a project footprint built to GeneSiC's layout: 2.16 x 2.26 mm pads, 2.74 mm gap (centres +/-2.45 mm).
- Even 2.74 mm is far below IPC-2221B guidance for uncoated terminations at ~2.6 kV, so plan conformal coat or potting over the clamp, and consider a routed slot between the pads.
