"""Rev B PRS circuit model: netlist builders + ngspice batch runner.

All component values come from PRS_RevB_architecture_proposal.md (Rev B, 18 Oct 2026)
unless marked ASSUMED. See RevB_simulation_report.md for the reasoning.
"""
import os, subprocess, tempfile, math, re
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
NETDIR = os.path.join(HERE, "netlists")
OUTDIR = os.path.join(HERE, "out")
os.makedirs(NETDIR, exist_ok=True); os.makedirs(OUTDIR, exist_ok=True)

MU0 = 4e-7 * math.pi

# ---------------------------------------------------------------- parameters
P = dict(
    # Stage 1 (doc s.3, s.1)
    V0a=1.1e3, C0a=96e-9, n=31.0,
    t_xfmr=1.0e-6,            # transformer charges C1 in ~1 us (doc)
    Lm_pri=1e-3,              # ASSUMED magnetising L (primary); core saturation not modelled
    C1=100e-12, C2=100e-12, C3=100e-12, Rbleed=10e6,
    L1s=81e-6, L2s=3.2e-6,    # SR1, SR2 saturated L (doc: transfer L for 200 ns / 40 ns)
    VS1=17e-3,                # SR1 hold-off (doc: 34 kV x 1 us x 1/2)
    VS2=3.4e-3,               # SR2 hold-off, = 34 kV x 200 ns x 1/2 (same rule; not stated in doc)
    VS3=0.68e-3,              # SR3 hold-off (doc)
    unsat_ratio12=1000.0,     # ASSUMED Lunsat/Lsat for wound SR1/SR2
    L3s=10e-9,                # SR3 single-turn ferrite, saturated (doc ~10 nH; 190 nH allowed)
    L3u=1e-3,                 # SR3 'ideal' unsaturated L (user instruction: ideal saturating L)
    Cblock=1e-9, Cplug=15e-12,
    # Stage 2 (doc s.2, s.4, s.5, s.6)
    V0b=4e3, C0b=62.5e-9,
    N=6, Ae=8e-4,             # SRiso: N=6, ~8 cm2 (effective iron area)
    le=0.22,                  # ASSUMED mean path (toroid ~OD 90/ID 50 mm)
    VSiso=9.5e-3,             # forward budget from -Bs reset (doc: 1.5 spike + 8 delay)
    Lsat=0.24e-6, Lloop=0.03e-6,
    Cw=1.5e-12,               # SRiso winding capacitance 1.5-3 pF
    # nanocrystalline dynamic loss (model 'eddy'): H = Hc*tanh(.) + ke*dB/dt
    Hc=2.5,                   # A/m, FT-3M datasheet DC coercivity
    ke=4.5e-5,                # A.s/(m.T): classical d^2/(12 rho) for 18 um, 1.2 uOhm.m = 2.25e-5, x2 excess (ASSUMED)
    model="eddy",             # 'eddy' (primary) or 'ttu' (port of TTU behavioural core)
    # TTU (FT-3KM parameters from TTU package, scaled to this core; B-axis re-centred, see report)
    k1=5e-5, k3=8.0, Gamma=0.21, ttu_R0=200.0, ttu_C0=0.8e-9, ttu_Ae0=150e-6, ttu_Le0=205e-3, ttu_N0=2,
    ttu_latch=True,
    flux0=0.0,                # SRiso initial forward flux linkage offset (V.s) - for jitter study
    # Channel
    Vbd=27.5e3,               # breakdown magnitude (doc: 25 kV x 1.1 cold); 'peak' option
    Rch=1.0, Roff=1e9, t_close_ramp=1e-9,
    t_quench=None,            # absolute time channel reopens
    t_rebreak=None,           # absolute time channel re-closes (from pass detection)
    V_rebreak=2.1e3,          # hot-channel re-break (doc)
    # sim control
    tstop=None, tmax=0.25e-9,
)

def sp(x, w):   # smooth ramp max(x,0) for ngspice B-source
    return f"(uramp({x}) + {w}*ln(1+exp(-abs({x})/{w})))"

def satl(name, a, b, Ls, Lu, VS, w_frac=0.002):
    """Lossless saturable inductor reset to the reverse knee: lambda in [0,VS] is the
    unsaturated region (Lu); above VS forward saturation (Ls); below 0 reverse saturation (Ls)."""
    w = VS * w_frac
    k = 1.0/Ls - 1.0/Lu
    lam = f"v(lam_{name})"
    return f"""* saturable inductor {name}: Ls={Ls:g} Lu={Lu:g} VS={VS:g}
G_{name} 0 lam_{name} {a} {b} 1
C_{name} lam_{name} 0 1
R_{name} lam_{name} 0 1e15
B_{name} {a} {b} I = {lam}/{Lu:g} + {k:g}*({sp(f'({lam}-{VS:g})', w)} - {sp(f'(-{lam}-{10*w:g})', w)} + {w*math.log1p(math.exp(-10)):g})
"""

def sriso(p, a, b):
    """SRiso between a (bank side) and b (plug side): Lsat+Lloop air/leakage in series with core element.
    Winding capacitance Cw across the whole reactor."""
    N, Ae, le = p["N"], p["Ae"], p["le"]
    VS = p["VSiso"]; dB = VS/(N*Ae)
    lines = [f"* SRiso model={p['model']} N={N} Ae={Ae} le={le} VS={VS} (dB={dB:.3f} T)",
             f"L_iso_air {a} iso_m {p['Lsat']+p['Lloop']:g}",
             f"C_iso_w {a} cw_s {p['Cw']:g}", f"V_iso_cw cw_s {b} 0",
             f"G_iso_lam 0 lam_iso iso_m {b} 1", "C_iso_lam lam_iso 0 1", "R_iso_lam lam_iso 0 1e15"]
    Bf = f"(v(lam_iso)+{p['flux0']:g})/{N*Ae:g}"     # forward flux density from reset [T]
    dBdt = f"(v(iso_m,{b})/{N*Ae:g})"
    sc = le/N   # H -> winding current
    wall_L = 2e-9  # steep wall (core side) in V.s/A terms; Lsat in series carries saturated current
    w = VS*0.002
    if p["model"] == "eddy":
        lam = f"(v(lam_iso)+{p['flux0']:g})"
        lines.append(f"B_iso_core iso_m {b} I = {sc:g}*({p['Hc']:g}*tanh({dBdt}/0.01e6) + {p['ke']:g}*{dBdt})"
                     f" + (1/{wall_L:g})*({sp(f'({lam}-{VS:g})', w)} - {sp(f'(-{lam}-{10*w:g})', w)} + {w*math.log1p(math.exp(-10)):g})")
    elif p["model"] == "ttu":
        # TTU Core_Model.sub equations (Kelp et al.), ported:
        #  mu(B)=1/(k1*exp(k2*B^2)+k3);  A=alpha*Ae;  alpha=1/(dBdt_peak[T/us]/Gamma+1);
        #  mmf = flux*Le/(mu*A)  (+Lc*dflux/dt, negligible: Lc=1nH);  RC branch across winding.
        # Re-centred on the middle of the forward swing so the reset point (-Bs) is B_f=0 and the knees
        # sit at B_f=-0.05 T and B_f=dB+0.05 T; k2 rescaled so k1*exp(k2*x^2)=k3 at the knee.
        c = dB/2; xk = dB/2 + 0.05
        k2 = math.log(p["k3"]/p["k1"]) / xk**2
        scale = (N/p["ttu_N0"])**2 * (Ae/p["ttu_Ae0"]) / (le/p["ttu_Le0"])
        Rr = p["ttu_R0"]*scale; Cr = p["ttu_C0"]/scale
        lines += [f"* TTU scaled: k2={k2:.4g} R={Rr:.4g} C={Cr:.4g}",
                  f"R_iso_rc iso_m iso_rc {Rr:g}", f"C_iso_rc iso_rc {b} {Cr:g}"]
        if p["ttu_latch"]:   # TTU peak detector: diode + 1uF || 10k (tau = 10 ms)
            lines += [f"B_iso_abs iso_abs 0 V = abs({dBdt})/1e6",
                      "D_iso_l iso_abs iso_lat DIDEAL", "C_iso_l iso_lat 0 1u", "R_iso_l iso_lat 0 10k",
                      ".model DIDEAL D(Is=1e-14 N=0.01)"]
            rate = "v(iso_lat)"
        else:   # instantaneous rate, 20 ns smoothing
            lines += [f"B_iso_abs iso_abs 0 V = abs({dBdt})/1e6", "R_iso_sm iso_abs iso_lat 20", "C_iso_sm iso_lat 0 1n"]
            rate = "v(iso_lat)"
        x = f"({Bf}-{c:g})"
        mu = f"(1/({p['k1']:g}*exp(min({k2:g}*{x}*{x},60))+{p['k3']:g}))"
        alpha = f"(1/({rate}/{p['Gamma']:g}+1))"
        lines.append(f"B_iso_core iso_m {b} I = {sc:g}*{Bf}/({alpha}*{mu})")
    elif p["model"] == "ttu_lt":
        # Original TTU LTspice subcircuit (Core_Model.sub, Kelp et al.), only change: ut(B) re-centred by Bc.
        c = dB/2; xk = dB/2 + 0.05
        k2 = math.log(p["k3"]/p["k1"]) / xk**2
        scale = (N/p["ttu_N0"])**2 * (Ae/p["ttu_Ae0"]) / (le/p["ttu_Le0"])
        Rr = p["ttu_R0"]*scale; Cr = p["ttu_C0"]/scale
        lines = [l for l in lines if not l.startswith(("G_iso_lam", "C_iso_lam", "R_iso_lam"))]
        lines += [".include Core_Model_recentred.sub", ".model D D",
                  f"X_iso iso_al iso_B iso_m {b} iso_fl iso_H iso_ib iso_irc Core_Model_RC Ae={Ae:g} Le={le:g} "
                  f"k1={p['k1']:g} k2={k2:.6g} k3={p['k3']:g} Gamma={p['Gamma']:g} Lc=1n R={Rr:.6g} C={Cr:.6g} Nw={N} Bc={c:.6g}"]
    else:
        raise ValueError(p["model"])
    return "\n".join(lines) + "\n"

def channel(p, node):
    """Channel: conductance g(t)/Rch between node and ground. g is a PWL 0..1 built from
    breakdown / quench / re-break times (determined by multi-pass detection)."""
    pts = [(0, 0)]
    tr = p["t_close_ramp"]
    if p.get("t_bd") is not None:
        t = p["t_bd"]; pts += [(t, 0), (t+tr, 1)]
        if p["t_quench"] is not None:
            tq = p["t_quench"]; pts += [(tq, 1), (tq+tr, 0)]
            if p["t_rebreak"] is not None:
                trb = p["t_rebreak"]; pts += [(trb, 0), (trb+tr, 1)]
    pwl = " ".join(f"{t:.6e} {v}" for t, v in pts)
    return (f"V_chg chg 0 PWL({pwl})\n"
            f"B_ch {node} 0 I = v({node})*(v(chg)/{p['Rch']:g} + 1/{p['Roff']:g})\n")

def netlist(p, blocks="full"):
    n = p["n"]
    Cs01 = p["C0a"]*p["C1"]*n*n/(p["C0a"]+p["C1"]*n*n)
    Lleak = (p["t_xfmr"]/math.pi)**2/Cs01
    s = [f"* PRS Rev B  blocks={blocks}  model={p['model']}"]
    s.append(".options method=gear reltol=1e-4 abstol=1e-9 vntol=1e-4 itl4=200 maxord=2")
    if blocks in ("full", "stage1"):
        s += [f"C0a a0 0 {p['C0a']:g} IC={p['V0a']:g}",
              "D_igbt a0 a1 DSW", ".model DSW D(Is=1e-12 N=1 Rs=1m)",
              f"L_leak a1 a2 {Lleak:g}",
              f"L_pri a2 0 {p['Lm_pri']:g}", f"L_sec 0 n1 {p['Lm_pri']*n*n:g}",   # inverted: n1 goes negative
              "K_x L_pri L_sec 1",
              f"C1 n1 0 {p['C1']:g}", f"C2 n2 0 {p['C2']:g}", f"C3 n3 0 {p['C3']:g}",
              f"R_bleed n3 0 {p['Rbleed']:g}"]
        s.append(satl("SR1", "n2", "n1", p["L1s"], p["L1s"]*p["unsat_ratio12"], p["VS1"]))
        s.append(satl("SR2", "n3", "n2", p["L2s"], p["L2s"]*p["unsat_ratio12"], p["VS2"]))
        # SR3 is driven negative: its forward direction is n3 -> x (current flows x -> n3); orient so forward = v(x,n3)>0
        s.append(satl("SR3", "x", "n3", p["L3s"], p["L3u"], p["VS3"]))
        vb = p['V0b'] if blocks == "full" else 0.0
        s += [f"C_block x P {p['Cblock']:g} IC={-vb:g}"]   # v(x)-v(P) = -4 kV at rest (full chain)
    if blocks in ("full", "stage2"):
        s += [f"C0b bk 0 {p['C0b']:g} IC={p['V0b']:g}",
              f"C_plug P 0 {p['Cplug']:g} IC={p['V0b']:g}"]
        s.append(sriso(p, "bk", "P"))
        s.append(channel(p, "P"))
    if blocks == "stage1":   # stage 1 alone into plug (no SRiso / bank); plug starts at 0
        s += [f"C_plug P 0 {p['Cplug']:g} IC=0", f"C_iso_w P 0 {p['Cw']:g}"]
        s.append(channel(p, "P"))
    return "\n".join(s) + "\n"

SAVE_FULL = ["v(n1)", "v(n2)", "v(n3)", "v(x)", "v(P)", "v(bk)", "v(lam_iso)", "v(lam_SR1)", "v(lam_SR2)", "v(lam_SR3)",
             "i(L_iso_air)", "i(V_iso_cw)", "v(chg)", "v(a0)", "i(L_leak)", "v(iso_m)"]

def run(p, blocks="full", tag="run", save=None, extra=""):
    if p.get("simulator", "ngspice") == "ltspice":
        return run_lt(p, blocks, tag)
    if save is None:
        save = [v for v in SAVE_FULL if not (blocks == "stage1" and ("iso" in v or "bk" in v)) and
                not (blocks == "stage2" and any(k in v for k in ["n1", "n2", "n3", "SR", "(x)", "a0", "leak"]))]
    tstop = p["tstop"]
    net = netlist(p, blocks) + extra
    out = os.path.join(OUTDIR, f"{tag}.dat")
    ctl = (".control\nset wr_singlescale\nset wr_vecnames\noption numdgt=9\n"
           f"tran 0.05n {tstop:.6e} 0 {p['tmax']:.3e} uic\n"
           f"wrdata {out} {' '.join(save)}\nquit\n.endc\n.end\n")
    fn = os.path.join(NETDIR, f"{tag}.cir")
    with open(fn, "w") as f:
        f.write(net + ctl)
    r = subprocess.run(["ngspice", "-b", fn], capture_output=True, text=True, timeout=1800)
    log = r.stdout + r.stderr
    with open(os.path.join(OUTDIR, f"{tag}.log"), "w") as f:
        f.write(log)
    if not os.path.exists(out) or "simulation interrupted" in log.lower() or "timestep too small" in log.lower():
        raise RuntimeError(f"ngspice failed for {tag}: see out/{tag}.log\n" + log[-2000:])
    d = np.loadtxt(out, skiprows=1)
    with open(out) as f:
        names = f.readline().split()
    res = {nm: d[:, i] for i, nm in enumerate(names)}
    res["t"] = res.pop("time")
    return res

def run_lt(p, blocks, tag):
    import ltspice_run as L, shutil
    shutil.copy(os.path.join(HERE, "ttu", "Core_Model_recentred.sub"), L.WDIR)
    q = dict(p); assert q["model"] == "ttu_lt"
    net = netlist(q, blocks).replace(" maxord=2", "")
    saves = ["V(n1)", "V(n2)", "V(n3)", "V(x)", "V(P)", "V(bk)", "V(iso_B)", "I(L_iso_air)", "I(V_iso_cw)", "V(chg)", "V(iso_m)"]
    if blocks == "stage2":
        saves = [x for x in saves if x not in ("V(n1)", "V(n2)", "V(n3)", "V(x)")]
    net += f".tran 0 {q['tstop']:.6e} 0 {q['tmax']:.3e} uic\n.save {' '.join(saves)}\n.end\n"
    with open(os.path.join(NETDIR, tag + "_lt.cir"), "w") as f: f.write(net)
    r, log = L.run(net, tag)
    with open(os.path.join(OUTDIR, tag + "_lt.log"), "w") as f: f.write(log)
    if "Simulation Failed" in log or "Convergence Failure" in log:
        raise RuntimeError(f"LTspice failed for {tag}:\n{log[-1200:]}")
    out = {"t": r["time"]}
    for k in saves:
        out[k.lower().replace("v(p)", "v(P)").replace("i(l_iso_air)", "i(L_iso_air)").replace("i(v_iso_cw)", "i(V_iso_cw)")] = r[k.lower()]
    out["v(lam_iso)"] = r["v(iso_b)"] * q["N"] * q["Ae"]
    return out
