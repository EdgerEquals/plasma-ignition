#!/usr/bin/env python3
"""Rev B Plasma Ignition v2 follow-up modelling (resumable; checkpoints to results/v2_checkpoint.jsonl).

    python3 run_v2.py [--items 1,2,3] [--fresh] [--plots-only]
    (also: python3 run_all.py --v2)

 1. no-re-break quench failure mode: plug-node mitigations
 2. SR3 as a real NiZn ferrite coax switch: geometry / material sweep
 3. C_block recovery between shots (150 Hz, 200-600 Hz burst) with lossy cores and bleed options
"""
import sys, os, json, math, time, copy, argparse
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import prs_model as m, analysis as a

PLOTS = os.path.join(HERE, "plots"); RES = os.path.join(HERE, "results")
CK = os.path.join(RES, "v2_checkpoint.jsonl")
MU0 = m.MU0

def P(**kw):
    p = copy.deepcopy(m.P); p.update(kw); return p

def scal(d):
    o = {}
    for k, v in d.items():
        if isinstance(v, np.ndarray) or callable(v): continue
        if isinstance(v, (np.floating, np.integer)): v = float(v)
        if isinstance(v, dict): v = scal(v)
        o[k] = v
    return o

def load_ck():
    D = {}
    if os.path.exists(CK):
        for l in open(CK):
            try: d = json.loads(l); D[d["tag"]] = d
            except Exception: pass
    return D

def save_ck(d):
    with open(CK, "a") as f: f.write(json.dumps(scal(d), default=str) + "\n")

def cumtrapz(y, t): return a.cumtrapz(y, t)

# ====================================================================== ITEM 1: quench mitigations
def mit_net(kind, prm, t_bd=None):
    """Return (netlist text, save list) for a plug-node mitigation."""
    if kind == "none":
        return "", []
    if kind == "holddown":      # AC-coupled hold-down: P - R_h - L_h - C_h - gnd, C_h pre-charged to +4 kV (rest value)
        R, L, C = prm["R"], prm["L"], prm["C"]
        return (f"V_mit P hd1 0\nR_h hd1 hd2 {R:g}\nL_h hd2 hd3 {L:g}\nC_h hd3 0 {C:g} IC=4000\n", ["i(V_mit)"])
    if kind == "clamp":         # HV blocking rectifier + avalanche/TVS stack to ground, conducts above +X kV; 2 pF stack capacitance
        X, Ron = prm["X"], prm.get("Ron", 20.0)
        return (f"V_mit P cl1 0\nB_cl cl1 0 I = {sp_on('v(cl1)', X)}/{Ron:g}\nC_clj P 0 2p IC=4000\n", ["i(V_mit)"])
    if kind == "crowbar":       # timed backup discharge: triggered switch + R_d to ground, fires at t_bd + t_fire if not re-broken
        tf = t_bd + prm["t_fire"]; Rd = prm.get("Rd", 2.0)
        return (f"V_mit P cb1 0\nV_cbg cbg 0 PWL(0 0 {tf:.6e} 0 {tf+10e-9:.6e} 1)\nB_cb cb1 0 I = v(cb1)*(v(cbg)/{Rd:g}+1e-9)\n", ["i(V_mit)"])
    if kind == "kick":          # SRiso forward kick winding (referred current into the core element) at t_bd + t_fire
        tf = t_bd + prm["t_fire"]; I = prm["I"]; w = prm.get("w", 300e-9)
        return (f"I_kick P iso_m PWL(0 0 {tf:.6e} 0 {tf+20e-9:.6e} {I:g} {tf+w:.6e} {I:g} {tf+w+20e-9:.6e} 0)\nV_mit P mt0 0\nR_mitdummy mt0 0 1e12\n", ["i(V_mit)"])
    if kind == "diode":         # anti-reversal diode stack across SRiso (anode at plug node, cathode at bank), 60 kV, Cd pF
        Ron, Cd = prm.get("Ron", 2.0), prm.get("Cd", 2e-12)
        return (f"V_mit P dd1 0\nD_ar dd1 bk DAR\n.model DAR D(Is=1e-12 N=6 Rs={Ron:g} BV=1e6)\nC_dd P bk {Cd:g}\n", ["i(V_mit)"])
    if kind == "rclamp":        # diode stack from plug node to a capacitor-backed rail at X (just above the 4 kV bank), 2 pF stack C
        X, Ron = prm["X"], prm.get("Ron", 2.0)
        return (f"V_mit P rc1 0\nD_rc rc1 rcv DRC\n.model DRC D(Is=1e-12 N=6 Rs={Ron:g} BV=1e6)\nV_rc rcv 0 {X:g}\nC_rcd P 0 2p IC=4000\n", ["i(V_mit)"])
    if kind == "holddown+clamp":
        n1, s1 = mit_net("holddown", prm); n2, _ = mit_net("clamp", prm)
        return n1 + n2.replace("V_mit", "V_mit2"), s1 + ["i(V_mit2)"]
    raise ValueError(kind)

def sp_on(v, X):  # smooth max(v-X,0)
    return f"(uramp({v}-{X:g}) + 20*ln(1+exp(-abs({v}-{X:g})/20)))"

def simulate_mit(p, tag, kind, prm, tq_rel, rebreak_V, t_after=13e-6):
    """Like analysis.simulate, with the mitigation network included in every pass."""
    net0, sv = mit_net(kind, prm, t_bd=0.0)
    p = dict(p); p["extra_save"] = list(p.get("extra_save", [])) + sv
    DUMMY = "V_mit P mt0 0\nR_mitd mt0 0 1e12\n"
    p["extra_net"] = net0 if kind not in ("crowbar", "kick") else DUMMY
    info, r1 = a.find_breakdown(p, tag)
    q = dict(p); q["t_bd"] = info["t_bd"]; q["tstop"] = info["t_bd"] + t_after
    if kind in ("crowbar", "kick"): q["extra_net"], _ = mit_net(kind, prm, t_bd=info["t_bd"])
    q["t_quench"] = None if tq_rel is None else info["t_bd"] + tq_rel
    r = m.run(q, "full", tag)
    if tq_rel is not None and rebreak_V is not None:
        trb = a.first_cross(r["t"], np.abs(r["v(P)"]), rebreak_V, q["t_quench"] + 2e-9, "up")
        info["t_rebreak"] = trb
        if trb is not None:
            q["t_rebreak"] = trb
            if kind in ("crowbar", "kick") and trb < info["t_bd"] + prm["t_fire"]:
                q["extra_net"] = DUMMY   # re-broke before the fallback timer: fallback not triggered
            r = m.run(q, "full", tag)
    met = a.metrics(q, r, info)
    t, vP = r["t"], r["v(P)"]
    o = {k: v for k, v in met.items() if not isinstance(v, np.ndarray)}
    o.update({k: v for k, v in info.items()})
    Ech = met["Ech"]
    imit = r.get("i(V_mit)", np.zeros_like(t)) + r.get("i(v_mit2)", r.get("i(V_mit2)", np.zeros_like(t)))
    vm = (vP - r["v(bk)"]) if kind == "diode" else vP
    Emit = cumtrapz(vm*imit, t)
    tbd = info["t_bd"]
    if q["t_quench"] is not None:
        w = t > q["t_quench"]
        o["Vnode_max_after_quench"] = float(vP[w].max()); o["Vnode_min_after_quench"] = float(vP[w].min())
    o["Vnode_max_after_bd"] = float(vP[t > tbd + 30e-9].max())
    o["E_mit_total"] = float(Emit[-1])
    ib = np.searchsorted(t, tbd)
    o["E_mit_before_bd"] = float(Emit[ib])
    o["E_ch_end"] = float(Ech[-1])
    o["frac_ch_of_bank"] = float((Ech[-1] - Ech[np.searchsorted(t, tbd + 30e-9)]) / met["E_bank0"])
    o["E_bank_end"] = float(0.5*q["C0b"]*r["v(bk)"][-1]**2)
    o["fires"] = met.get("t_sat") is not None
    return o, r, q

def item1(ck, quick=False):
    out = []
    mits = [("none", {}), ]
    for C in (2e-9, 5e-9, 10e-9):
        for L in (10e-6, 30e-6, 100e-6):
            mits.append(("holddown", dict(R=100.0, L=L, C=C)))
    mits += [("holddown", dict(R=30.0, L=30e-6, C=5e-9)), ("holddown", dict(R=300.0, L=30e-6, C=5e-9)),
             ("clamp", dict(X=6e3)), ("clamp", dict(X=10e3)),
             ("holddown+clamp", dict(R=100.0, L=30e-6, C=5e-9, X=10e3)),
             ("holddown", dict(R=1000.0, L=1e-6, C=5e-9)),
             ("diode", dict(Ron=2.0, Cd=2e-12)), ("diode", dict(Ron=2.0, Cd=5e-12)),
             ("diode", dict(Ron=30.0, Cd=2e-12)), ("diode", dict(Ron=100.0, Cd=2e-12)),
             ("diode", dict(Ron=300.0, Cd=2e-12)), ("diode", dict(Ron=1000.0, Cd=2e-12)),
             ("rclamp", dict(X=4.4e3, Ron=2.0)), ("rclamp", dict(X=5e3, Ron=2.0)), ("rclamp", dict(X=6e3, Ron=2.0)),
             ("rclamp", dict(X=4.4e3, Ron=10.0)),
             ("crowbar", dict(t_fire=3.0e-6, Rd=2.0)),
             ("kick", dict(t_fire=2.0e-6, I=15.0, w=300e-9))]
    scen = [("normal", None, None), ("q1_rb2.1", 1.0e-6, 2.1e3), ("q1_rb6", 1.0e-6, 6e3),
            ("q1_rb12", 1.0e-6, 12e3), ("q1_norb", 1.0e-6, None), ("q0.5_norb", 0.5e-6, None)]
    runs = [("eddy", kind, prm) for kind, prm in mits]
    # spot check with the TTU behavioural core (largest no-re-break ring-up in v1)
    runs += [("ttu", k, q) for k, q in (("none", {}), ("diode", dict(Ron=300.0, Cd=2e-12)), ("diode", dict(Ron=1000.0, Cd=2e-12)),
                                        ("clamp", dict(X=10e3)), ("holddown", dict(R=100.0, L=30e-6, C=5e-9)),
                                        ("rclamp", dict(X=4.4e3, Ron=2.0)), ("rclamp", dict(X=5e3, Ron=2.0)))]
    for model, kind, prm in runs:
        if True:
            pid = kind + "".join(f"_{k}{v:g}" for k, v in prm.items())
            for sc, tq, rb in scen:
                if kind in ("crowbar", "kick") and sc == "normal": continue
                if kind not in ("none",) and kind != "holddown" and sc in ("q0.5_norb",): continue
                tag = f"v2m_{model}_{pid}_{sc}"
                if tag in ck and ck[tag].get("ok"): out.append(ck[tag]); continue
                t0 = time.time()
                for tmax in (0.1e-9, 0.05e-9, 0.02e-9):     # retry finer on 'timestep too small'
                    try:
                        o, r, q = simulate_mit(P(model=model, tmax=tmax), tag, kind, prm, tq, rb)
                        d = dict(tag=tag, ok=True, item=1, model=model, kind=kind, prm=prm, scen=sc, tq=tq, rebreak_V=rb, tmax=tmax, **o)
                        break
                    except Exception as e:
                        d = dict(tag=tag, ok=False, item=1, model=model, kind=kind, prm=prm, scen=sc, err=str(e)[-300:])
                d["runtime_s"] = time.time() - t0
                save_ck(d); ck[tag] = scal(d); out.append(ck[tag])
                print(f"  {tag:60s} ok={d['ok']} Vpk_nobd={d.get('Vnode_peak_nobd',0)/1e3 if d.get('ok') else 0:.1f}kV "
                      f"Vmax_q={(d.get('Vnode_max_after_quench') or 0)/1e3:.1f}kV fires={d.get('fires')} delay={d.get('delay')} "
                      f"Ech_frac={d.get('frac_ch_of_bank')} {d['runtime_s']:.0f}s", flush=True)
    return out

# ====================================================================== ITEM 2: SR3 as a NiZn ferrite coax switch
# Material data (hot = ~100 C), see report section 9.2 for sources.
MAT = {
    # name: Bs_hot [T], usable bias-reset swing dB_hot [T], static loop slope mu_D, Hc [A/m], Tc [C]
    "4B1":     dict(Bs=0.31, dB=0.55, mui=250.0,  Hc=100.0, Tc=250, note="Ferroxcube 4B1 NiZn, Bs 360/310 mT @25/100C, mu_i 250"),
    "4C65":    dict(Bs=0.34, dB=0.60, mui=125.0,  Hc=200.0, Tc=350, note="Ferroxcube 4C65 NiZn, Bs 380/340 mT @25/100C, mu_i 125"),
    "CMD5005": dict(Bs=0.33, dB=0.60, mui=2100.0, Hc=9.5,   Tc=130, note="National/Magnetics CMD5005 NiZn pulse ferrite @25C ONLY (Tc 130C)"),
}
SW_NOM = 20e-6   # switching coefficient 0.25 Oe.us = 19.9 A.us/m (NBS TN-90; consistent with ~3 Oe for 100 ns, KEK/CAT)

def sr3_geom(mat, N, ID, OD, fvs, Sw=SW_NOM, VS_req=0.68e-3, lead=5e-9, ins_in=2e-3, ins_out=8e-3):
    if mat.startswith("gen_mu"):   # hypothetical material: 4C65 hot swing, chosen mu, Hc 50 A/m
        M = dict(MAT["4C65"]); M.update(mui=float(mat[6:]), Hc=50.0)
    else:
        M = MAT[mat]
    le = math.pi*(ID+OD)/2; hw = (OD-ID)/2
    A = fvs*VS_req/(N*M["dB"])           # iron area needed for fvs x the hold-off budget
    length = A/hw
    a_ = ID/2 - ins_in; b_ = OD/2 + ins_out
    Lair = N*N*2e-7*length*math.log(b_/a_) + lead
    ke = Sw/M["dB"]
    core = dict(N=N, A=A, le=le, dB=M["dB"], Hc=M["Hc"], ke=ke, mui=M["mui"], Lair=Lair)
    # small-signal figures of merit (per core, from reset): static L, viscous loss resistance
    Lstat = MU0*M["mui"]*N*N*A/le; Rvisc = N*N*A/(ke*le)
    return core, dict(mat=mat, N=N, ID=ID, OD=OD, fvs=fvs, Sw=Sw, A_cm2=A*1e4, length_mm=length*1e3, le_m=le,
                      Lsat_nH=Lair*1e9, Lstat_uH=Lstat*1e6, Rvisc_ohm=Rvisc, VS=N*A*M["dB"],
                      Ibias_At=(M["dB"]/2/(MU0*M["mui"]) + M["Hc"] + 300)*le)   # A-turns to hold -Bs (+300 A/m margin)

def edge_metrics(t, v, t_from=0.9e-6, t_to=1.45e-6):
    w = (t > t_from) & (t < t_to); idx = np.where(w)[0]
    i0 = idx[np.argmin(v[idx])]; vpk = v[i0]
    j = i0
    while j > idx[0] and v[j] < 0.9*vpk: j -= 1
    t90 = t[j]
    while j > idx[0] and v[j] < 0.1*vpk: j -= 1
    t10 = t[j]
    dv = np.gradient(v[idx], t[idx])
    j = i0
    while j > idx[0] and v[j] < 0.5*vpk: j -= 1
    return dict(Vpk=vpk, t_pk=t[i0], edge1090=t90 - t10, edge5090=t90 - t[j], dvdt_max=-dv.min())

def item2(ck):
    out = []
    grid = []
    for mat in ("4B1", "4C65"):
        for N in (1, 2, 3, 4):
            for (ID, OD) in ((25e-3, 60e-3), (25e-3, 80e-3), (15e-3, 40e-3)):
                for fvs in (1.0, 1.5):
                    grid.append((mat, N, ID, OD, fvs, SW_NOM))
    for N in (1, 2, 3, 4): grid.append(("CMD5005", N, 25e-3, 60e-3, 1.0, SW_NOM))
    for Sw in (10e-6, 40e-6):
        for N in (1, 3): grid.append(("4C65", N, 25e-3, 60e-3, 1.0, Sw))
    # more turns (Lsat grows ~linearly with N at fixed hold-off because the stack gets thinner)
    for mat in ("4B1", "4C65", "CMD5005"):
        for N in (6, 8, 10, 12, 14, 16):
            grid.append((mat, N, 25e-3, 80e-3, 1.0, SW_NOM))
    for N in (8, 12):
        for Sw in (10e-6, 40e-6): grid.append(("4C65", N, 25e-3, 80e-3, 1.0, Sw))
        grid.append(("4C65", N, 25e-3, 80e-3, 1.5, SW_NOM))
    # generic 'what material would be needed' sweep (hypothetical NiZn, hot Bs as 4C65)
    for mui in (500.0, 1000.0, 2000.0, 5000.0):
        for Sw in (5e-6, 10e-6, 20e-6):
            for N in (4, 8, 12):
                grid.append((f"gen_mu{mui:g}", N, 25e-3, 80e-3, 1.0, Sw))
    for (mat, N, ID, OD, fvs, Sw) in grid:
        core, g = sr3_geom(mat, N, ID, OD, fvs, Sw)
        tag = f"v2f2_{mat}_N{N}_{ID*1e3:.0f}x{OD*1e3:.0f}_f{fvs:g}_Sw{Sw*1e6:g}"
        if tag in ck and ck[tag].get("ok"): out.append(ck[tag]); continue
        t0 = time.time()
        try:
            p = P(tstop=1.45e-6, tmax=0.01e-9, sr3_model="ferrite", sr3_core=core)
            r = m.run(p, "stage1", tag)
            t = r["t"]; e = edge_metrics(t, r["v(P)"])
            lam = r["v(lam_SR3)"]; k = np.where(lam >= 0.98*core["N"]*core["A"]*core["dB"])[0]
            tf = t[k[0]] if len(k) else None
            v3 = r["v(n3)"]; i3 = np.argmin(v3)
            d = dict(tag=tag, ok=True, item=2, **g, **e, t_fire=tf, sat=bool(len(k)),
                     V_C3_pk=float(v3[i3]), t_C3_pk=float(t[i3]),
                     Vplug_at_fire=float(np.interp(tf, t, r["v(P)"])) if tf else None,
                     ring=float(e["Vpk"]/v3[i3]))
        except Exception as ex:
            d = dict(tag=tag, ok=False, item=2, **g, err=str(ex)[-300:])
        d["runtime_s"] = time.time()-t0
        save_ck(d); ck[tag] = scal(d); out.append(ck[tag])
        print(f"  {tag:40s} ok={d['ok']} L={g['Lsat_nH']:.0f}nH len={g['length_mm']:.0f}mm sat={d.get('sat')} "
              f"Vpk={(d.get('Vpk') or 0)/1e3:.1f}kV edge={(d.get('edge1090') or 0)*1e9:.2f}ns e5090={(d.get('edge5090') or 0)*1e9:.2f}ns pre={(d.get('Vplug_at_fire') or 0)/1e3:.1f}kV", flush=True)
    # full-chain (bias, C_block, SRiso, no breakdown) gap peak for representative designs
    fc = [("4C65", 4, 25e-3, 80e-3, 1.0, SW_NOM), ("4C65", 12, 25e-3, 80e-3, 1.0, SW_NOM), ("4C65", 16, 25e-3, 80e-3, 1.0, SW_NOM),
          ("4B1", 12, 25e-3, 80e-3, 1.0, SW_NOM), ("CMD5005", 16, 25e-3, 80e-3, 1.0, SW_NOM),
          ("gen_mu2000", 12, 25e-3, 80e-3, 1.0, 5e-6), ("gen_mu5000", 12, 25e-3, 80e-3, 1.0, 10e-6), ("gen_mu5000", 8, 25e-3, 80e-3, 1.0, 5e-6)]
    for (mat, N, ID, OD, fvs, Sw) in fc:
        core, g = sr3_geom(mat, N, ID, OD, fvs, Sw)
        tag = f"v2f2fc_{mat}_N{N}_{ID*1e3:.0f}x{OD*1e3:.0f}_f{fvs:g}_Sw{Sw*1e6:g}"
        if tag in ck and ck[tag].get("ok"): out.append(ck[tag]); continue
        try:
            p = P(tstop=1.6e-6, tmax=0.02e-9, sr3_model="ferrite", sr3_core=core)
            r = m.run(p, "full", tag)
            t = r["t"]; e = edge_metrics(t, r["v(P)"] - p["V0b"], 0.9e-6, 1.55e-6)
            lam = r["v(lam_SR3)"]; k = np.where(lam >= 0.98*core["N"]*core["A"]*core["dB"])[0]
            tf = t[k[0]] if len(k) else None
            d = dict(tag=tag, ok=True, item=2, full_chain=True, **g, **e, Vgap_pk=float(r["v(P)"].min()), sat=bool(len(k)),
                     Vplug_at_fire=float(np.interp(tf, t, r["v(P)"])) if tf else None)
        except Exception as ex:
            d = dict(tag=tag, ok=False, item=2, full_chain=True, **g, err=str(ex)[-300:])
        save_ck(d); ck[tag] = scal(d); out.append(ck[tag])
        print(f"  {tag:44s} ok={d['ok']} Vgap={(d.get('Vgap_pk') or 0)/1e3:.1f}kV edge={(d.get('edge1090') or 0)*1e9:.1f} e5090={(d.get('edge5090') or 0)*1e9:.1f} pre={(d.get('Vplug_at_fire') or 0)/1e3:.1f}", flush=True)
    return out

# ====================================================================== ITEM 3: C_block recovery between shots
# Realistic SR1/SR2: nanocrystalline (FT-3M class) tape cores, bias reset, eddy/viscous loss as SRiso (ke 4.5e-5);
# turns chosen so the geometric saturated L stays well inside the doc's 81 uH / 3.2 uH transfer inductances.
SR1_CORE = dict(N=100, A=17e-3/(100*2.0), le=0.20, dB=2.0, Hc=2.5, ke=4.5e-5, mui=5e4, Lair=81e-6)
SR2_CORE = dict(N=40, A=3.4e-3/(40*2.0), le=0.15, dB=2.0, Hc=2.5, ke=4.5e-5, mui=5e4, Lair=3.2e-6)

def recovery(st, T, cfg, tag):
    """Inter-shot network over T seconds. SR1..SR3 sit in bias-held reverse saturation -> their saturated L (+1 ohm);
    plug side held at +4 kV by the recharged bank through saturated SRiso; transformer secondary = magnetising L_sec
    with winding R_w and core-loss shunt R_c; C3 bleed R_bleed; optional R_x (x to ground)."""
    p = m.P; Lsec = p["Lm_pri"]*p["n"]**2
    lines = ["* inter-shot recovery",
             f"L_sec n1 nw {Lsec:g} IC={-st['I_Lsec']:g}", f"R_w nw 0 {cfg.get('R_w', 20.0):g}",
             f"C1 n1 0 {p['C1']:g} IC={st['V_C1']:g}", f"C2 n2 0 {p['C2']:g} IC={st['V_C2']:g}", f"C3 n3 0 {p['C3']:g} IC={st['V_C3']:g}",
             f"L1 n2 m1 {p['L1s']:g}", "R1 m1 n1 1", f"L2 n3 m2 {p['L2s']:g}", "R2 m2 n2 1", f"L3 x m3 {p['L3s']:g}", "R3 m3 n3 1",
             f"R_bleed n3 0 {cfg.get('Rbleed', p['Rbleed']):g}",
             f"C_block x P {p['Cblock']:g} IC={st['V_Cblock']:g}", f"V_P P 0 {p['V0b']:g}"]
    if cfg.get("R_c"): lines.append(f"R_c n1 0 {cfg['R_c']:g}")
    if cfg.get("R_x"): lines.append(f"R_x x 0 {cfg['R_x']:g}")
    net = "\n".join(lines) + "\n"
    out = os.path.join(m.OUTDIR, tag + ".dat")
    ctl = (".control\nset wr_singlescale\nset wr_vecnames\noption numdgt=9\n"
           f"tran {T/2000:.4e} {T:.6e} 0 {T/4000:.4e} uic\n"
           f"wrdata {out} v(n1) v(n2) v(n3) v(x) i(L_sec)\nquit\n.endc\n.end\n")
    fn = os.path.join(m.NETDIR, tag + ".cir"); open(fn, "w").write(net + ".options method=gear reltol=1e-5\n" + ctl)
    r = __import__("subprocess").run(["ngspice", "-b", fn], capture_output=True, text=True, timeout=600)
    d = np.loadtxt(out, skiprows=1); names = open(out).readline().split()
    R = {nm: d[:, i] for i, nm in enumerate(names)}
    e = {k: R[k][-1] for k in R}
    return dict(V_C1=e["v(n1)"], V_C2=e["v(n2)"], V_C3=e["v(n3)"], V_Cblock=e["v(x)"] - p["V0b"], I_Lsec=-e["i(L_sec)"]), R

def shot(ic, cfg, tag, lossy=True):
    p = P(tmax=0.1e-9, ic=ic, extra_save=["i(L_sec)"], R_x=cfg.get("R_x"), Rbleed=cfg.get("Rbleed", m.P["Rbleed"]))
    if lossy: p.update(sr12_model="lossy", sr1_core=SR1_CORE, sr2_core=SR2_CORE)
    for tmax in (0.1e-9, 0.05e-9):
        try:
            p["tmax"] = tmax
            o, r, q = simulate_mit(p, tag, "none", {}, None, None)
            break
        except Exception as ex:
            err = ex
    else:
        raise err
    t = r["t"]
    end = dict(V_C1=r["v(n1)"][-1], V_C2=r["v(n2)"][-1], V_C3=r["v(n3)"][-1], V_Cblock=r["v(x)"][-1] - r["v(P)"][-1],
               I_Lsec=r["i(L_sec)"][-1])
    Ex = cumtrapz(r["v(x)"]**2/cfg["R_x"], t)[-1] if cfg.get("R_x") else 0.0
    keep = {k: o.get(k) for k in ("Vnode_peak_nobd", "t_bd", "delay", "frac_first_half", "Ipk", "E_ch_total", "E_ch_stage1",
                                  "E_ch_stage2_total", "Vbank_at_sat")}
    keep["E_Rx_shot"] = Ex
    return keep, end, r

RECOV_CFGS = {
    "lossless_xfmr":       dict(),                         # only 10 MOhm C3 bleed + 20 ohm winding
    "xfmr_Rc1M":           dict(R_c=1e6),
    "xfmr_Rc200k":         dict(R_c=200e3),
    "Rc1M_Rx1M":           dict(R_c=1e6, R_x=1e6),
    "Rc1M_Rx300k":         dict(R_c=1e6, R_x=300e3),
    "Rc1M_Rx100k":         dict(R_c=1e6, R_x=100e3),
    "lossless_Rx100k":     dict(R_x=100e3),
}
RATES = [("150Hz", 150.0, 8), ("200Hz_burst", 200.0, 6), ("300Hz_burst", 300.0, 6), ("400Hz_burst", 400.0, 6), ("600Hz_burst", 600.0, 6)]

def item3(ck):
    out = []
    ic0 = dict(V_C1=0.0, V_C2=0.0, V_C3=0.0, V_Cblock=-m.P["V0b"], I_Lsec=0.0)
    for cname, cfg in RECOV_CFGS.items():
        for rname, f, nshot in RATES:
            tag = f"v2c_{cname}_{rname}"
            if tag in ck and ck[tag].get("ok"): out.append(ck[tag]); continue
            t0 = time.time(); shots = []; ic = dict(ic0)
            try:
                for k in range(nshot):
                    met, end, r = shot(ic, cfg, f"{tag}_s{k}")
                    st, R = recovery(end, 1.0/f - (r["t"][-1]), cfg, f"{tag}_r{k}")
                    shots.append(dict(k=k, ic=ic, **met, end=end, next=st,
                                      dV_end=end["V_Cblock"] + m.P["V0b"], dV_next=st["V_Cblock"] + m.P["V0b"]))
                    print(f"    {tag} shot {k}: V_Cb start {ic['V_Cblock']/1e3:+.2f} end {end['V_Cblock']/1e3:+.2f} next {st['V_Cblock']/1e3:+.2f} kV "
                          f"VC3 next {st['V_C3']/1e3:+.2f} kV  peak {met['Vnode_peak_nobd']/1e3:.1f} kV delay {met['delay']}", flush=True)
                    ic = st
                d = dict(tag=tag, ok=True, item=3, cfg=cname, rate=rname, f=f, shots=shots)
            except Exception as ex:
                d = dict(tag=tag, ok=False, item=3, cfg=cname, rate=rname, f=f, shots=shots, err=str(ex)[-300:])
            d["runtime_s"] = time.time() - t0
            save_ck(d); ck[tag] = scal(d); out.append(ck[tag])
            print(f"  {tag} ok={d['ok']} {d['runtime_s']:.0f}s", flush=True)
    return out

# ====================================================================== plots + tables
def _dat(tag):
    fn = os.path.join(m.OUTDIR, tag + ".dat")
    if not os.path.exists(fn): return None
    d = np.loadtxt(fn, skiprows=1); names = open(fn).readline().split()
    return {nm: d[:, i] for i, nm in enumerate(names)}

MIT_SHOW = [("none", "none", "k"), ("clamp_X10000", "clamp 10 kV (TVS)", "tab:orange"),
            ("holddown_R100_L3e-05_C5e-09", "hold-down 100R/30uH/5nF", "tab:purple"),
            ("diode_Ron2_Cd2e-12", "diode across SRiso (2R)", "tab:green"),
            ("rclamp_X4400_Ron2", "diode to 4.4 kV reservoir rail", "tab:blue"),
            ("rclamp_X5000_Ron2", "diode to 5 kV reservoir rail", "tab:cyan"),
            ("crowbar_t_fire3e-06_Rd2", "timed crowbar 2R @ +3us", "tab:red")]

def make_plots(ck):
    os.makedirs(PLOTS, exist_ok=True)
    made = []
    # ---------------- 09: quench mitigations
    fig, ax = plt.subplots(1, 3, figsize=(17, 5.2))
    for j, model in enumerate(("eddy", "ttu")):
        for pid, lab, c in MIT_SHOW:
            tag = f"v2m_{model}_{pid}_q1_norb"; r = _dat(tag)
            if r is None or tag not in ck or not ck[tag].get("ok"): continue
            tb = ck[tag]["t_bd"]
            ax[j].plot((r["time"]-tb)*1e6, r["v(P)"]/1e3, color=c, lw=1, label=lab)
        ax[j].set_xlim(-0.2, 13); ax[j].set_ylim(-25, 40); ax[j].grid(alpha=.3)
        ax[j].set_xlabel("time after breakdown [us]"); ax[j].set_ylabel("plug node V(P) [kV]")
        ax[j].set_title(f"No re-break after quench at +1 us ({'eddy core (primary)' if model=='eddy' else 'TTU core'})")
        ax[j].axhline(4, color="grey", ls=":", lw=.8)
    ax[0].legend(fontsize=8, loc="upper right")
    labs, vmax, deliv = [], [], []
    for pid, lab, c in MIT_SHOW:
        a1 = ck.get(f"v2m_eddy_{pid}_q1_norb", {}); a2 = ck.get(f"v2m_eddy_{pid}_normal", ck.get(f"v2m_eddy_none_normal", {}))
        if not a1.get("ok"): continue
        labs.append(lab.replace(" (TVS)", "").replace("across SRiso ", "")); vmax.append(a1["Vnode_max_after_quench"]/1e3)
        deliv.append(100*a2.get("frac_first_half", np.nan) if a2.get("ok") else np.nan)
    x = np.arange(len(labs))
    ax[2].bar(x-0.2, vmax, 0.4, label="node max, no re-break [kV]", color="tab:red")
    ax2 = ax[2].twinx(); ax2.bar(x+0.2, deliv, 0.4, label="normal-shot 1st half-cycle delivery [%]", color="tab:blue")
    ax[2].set_xticks(x); ax[2].set_xticklabels(labs, rotation=35, ha="right", fontsize=8)
    ax[2].set_ylabel("kV"); ax2.set_ylabel("%"); ax2.set_ylim(0, 100)
    ax[2].set_title("Eddy model: node overvoltage vs normal delivery"); ax[2].legend(loc="upper left", fontsize=8); ax2.legend(loc="upper right", fontsize=8)
    fig.tight_layout(); fn = os.path.join(PLOTS, "09_quench_mitigations.png"); fig.savefig(fn, dpi=130); plt.close(fig); made.append(fn)

    # ---------------- 10: SR3 ferrite
    F = [d for k, d in ck.items() if k.startswith("v2f2_") and d.get("ok")]
    fig, ax = plt.subplots(1, 3, figsize=(17, 5.2))
    sty = {"4B1": ("o", "tab:blue"), "4C65": ("s", "tab:green"), "CMD5005": ("^", "tab:red")}
    for mat, (mk, c) in sty.items():
        dd = [d for d in F if d["mat"] == mat and abs(d["Sw"]-SW_NOM) < 1e-9 and d["fvs"] == 1.0]
        ax[0].scatter([d["Lsat_nH"] for d in dd], [-d["Vpk"]/1e3 for d in dd], marker=mk, color=c, label=f"{mat} (Sw 20 A.us/m)" + (" [25C only]" if mat == "CMD5005" else ""))
        ax[1].scatter([d["Lsat_nH"] for d in dd], [d["edge5090"]*1e9 for d in dd], marker=mk, color=c)
    for mu, c in ((1000.0, "tab:olive"), (2000.0, "tab:purple"), (5000.0, "tab:brown")):
        for Sw, mk in ((5e-6, "P"), (10e-6, "X")):
            dd = [d for d in F if d["mat"] == f"gen_mu{mu:g}" and abs(d["Sw"]-Sw) < 1e-9]
            ax[0].scatter([d["Lsat_nH"] for d in dd], [-d["Vpk"]/1e3 for d in dd], marker=mk, color=c, label=f"hypothetical mu {mu:g}, Sw {Sw*1e6:g}")
            ax[1].scatter([d["Lsat_nH"] for d in dd], [d["edge5090"]*1e9 for d in dd], marker=mk, color=c)
    ax[0].axhline(55.9, color="k", ls="--", lw=.8); ax[0].text(5, 56.4, "ideal SR3 10 nH (v1 stage-1 block): 55.9 kV", fontsize=8)
    ax[0].set_ylim(25, 58); ax[0].set_xlim(0, 240)
    for k in (0, 1): ax[k].axvline(190, color="k", ls=":", lw=.8); ax[k].set_xlabel("SR3 saturated L (geometric + 5 nH lead) [nH]"); ax[k].grid(alpha=.3)
    ax[0].set_ylabel("|plug peak| stage-1 block [kV]"); ax[0].set_title("SR3 as NiZn ferrite: plug peak vs Lsat"); ax[0].legend(fontsize=7, loc="lower right")
    ax[1].set_ylabel("50-90 % edge [ns]"); ax[1].set_yscale("log"); ax[1].set_title("final edge (50-90 %); ideal 10 nH: ~0.5 ns")
    for tag, lab, c in (("val_stage1", "ideal SR3 10 nH (v1)", "k"), ("val_stage1_190n", "ideal SR3 190 nH (v1)", "grey"),
                        ("v2f2_4C65_N1_25x60_f1_Sw20", "4C65 1 turn 25/60 mm, 65 mm long", "tab:green"),
                        ("v2f2_4C65_N12_25x80_f1_Sw20", "4C65 12 turns 25/80 mm, 3.4 mm", "tab:olive"),
                        ("v2f2_CMD5005_N16_25x80_f1_Sw20", "CMD5005 16 turns (25C only)", "tab:red"),
                        ("v2f2_gen_mu5000_N12_25x80_f1_Sw5", "hypothetical mu 5000, Sw 5, 12 turns", "tab:brown")):
        r = _dat(tag)
        if r is None: continue
        ax[2].plot(r["time"]*1e9, r["v(P)"]/1e3, color=c, lw=1, label=lab)
        ax[2].plot(r["time"]*1e9, r["v(n3)"]/1e3, color=c, lw=.6, ls=":")
    ax[2].set_xlim(1150, 1450); ax[2].set_xlabel("time [ns]"); ax[2].set_ylabel("plug (solid) / C3 (dotted) [kV]")
    ax[2].set_title("stage-1 block waveforms"); ax[2].legend(fontsize=7); ax[2].grid(alpha=.3)
    fig.tight_layout(); fn = os.path.join(PLOTS, "10_sr3_ferrite.png"); fig.savefig(fn, dpi=130); plt.close(fig); made.append(fn)

    # ---------------- 11: C_block shot-to-shot
    C = {(d["cfg"], d["rate"]): d for k, d in ck.items() if k.startswith("v2c_") and d.get("ok")}
    rates = [r[0] for r in RATES]
    fig, ax = plt.subplots(2, len(rates), figsize=(20, 7.5), sharey="row")
    cols = dict(lossless_xfmr="k", xfmr_Rc1M="tab:orange", xfmr_Rc200k="tab:olive", Rc1M_Rx1M="tab:purple",
                Rc1M_Rx300k="tab:blue", Rc1M_Rx100k="tab:green", lossless_Rx100k="tab:cyan")
    for j, rate in enumerate(rates):
        for cfg, c in cols.items():
            d = C.get((cfg, rate))
            if not d: continue
            sh = d["shots"]
            v = [s["ic"]["V_Cblock"]/1e3 for s in sh] + [sh[-1]["next"]["V_Cblock"]/1e3]
            ax[0, j].plot(range(1, len(v)+1), v, "o-", color=c, ms=3, lw=1, label=cfg)
            ax[1, j].plot(range(1, len(sh)+1), [-s["Vnode_peak_nobd"]/1e3 for s in sh], "o-", color=c, ms=3, lw=1)
        ax[0, j].set_title(rate.replace("_", " ")); ax[0, j].axhline(-4, color="grey", ls=":")
        ax[1, j].set_xlabel("shot #"); ax[0, j].grid(alpha=.3); ax[1, j].grid(alpha=.3)
    ax[0, 0].set_ylabel("C_block voltage at shot start [kV] (ideal -4)"); ax[1, 0].set_ylabel("|gap peak| (no breakdown) [kV]")
    ax[0, 0].legend(fontsize=7); ax[1, 0].set_ylim(0, 50)
    fig.suptitle("C_block recovery between shots (lossy SR1/SR2, ideal SR3, bias reset assumed complete)")
    fig.tight_layout(); fn = os.path.join(PLOTS, "11_cblock_multishot.png"); fig.savefig(fn, dpi=130); plt.close(fig); made.append(fn)

    # ---------------- 12: recovery waveform example
    fig, ax = plt.subplots(1, 2, figsize=(14, 4.5))
    for cfg, c in (("lossless_xfmr", "k"), ("xfmr_Rc1M", "tab:orange"), ("Rc1M_Rx300k", "tab:blue"), ("lossless_Rx100k", "tab:cyan")):
        r = _dat(f"v2c_{cfg}_150Hz_r0")
        if r is None: continue
        ax[0].plot(r["time"]*1e3, (r["v(x)"] - 4000)/1e3, color=c, lw=.7, label=cfg)
        r = _dat(f"v2c_{cfg}_300Hz_burst_r0")
        if r is not None: ax[1].plot(r["time"]*1e3, (r["v(x)"] - 4000)/1e3, color=c, lw=.7, label=cfg)
    for k, tt in ((0, "after shot 1, 150 Hz (6.7 ms gap)"), (1, "after shot 1, 300 Hz burst (3.3 ms gap)")):
        ax[k].axhline(-4, color="grey", ls=":"); ax[k].set_xlabel("time after shot [ms]"); ax[k].set_ylabel("V_Cblock [kV]")
        ax[k].set_title("inter-shot recovery " + tt); ax[k].grid(alpha=.3); ax[k].legend(fontsize=8)
    fig.tight_layout(); fn = os.path.join(PLOTS, "12_cblock_recovery_waveforms.png"); fig.savefig(fn, dpi=130); plt.close(fig); made.append(fn)
    return made

def make_tables(ck):
    L = ["# v2 result tables (generated by run_v2.py)", ""]
    # ---- item 1
    L += ["## Item 1 - no-re-break quench mitigations (eddy core; quench at +1 us)", "",
          "| mitigation | gap peak, no bd [kV] | normal: 1st half-cycle delivery [%] | normal: channel energy / bank [%] | normal: energy into mitigation [mJ] | no re-break: node max [kV] | no re-break: node min [kV] | no re-break: stage 2 fires | no re-break: bank energy kept [mJ] | no re-break: energy into mitigation [mJ] | re-break only >12 kV: fires / delay [us] | TTU no re-break node max [kV] |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    pids = []
    for k in ck:
        if k.startswith("v2m_eddy_") and k.endswith("_q1_norb"): pids.append(k[len("v2m_eddy_"):-len("_q1_norb")])
    f = lambda x, s=1.0, n=1: "-" if x is None else f"{x*s:.{n}f}"
    for pid in pids:
        nb = ck.get(f"v2m_eddy_{pid}_q1_norb", {}); nm = ck.get(f"v2m_eddy_{pid}_normal") or ck.get("v2m_eddy_none_normal", {})
        r12 = ck.get(f"v2m_eddy_{pid}_q1_rb12", {}); tt = ck.get(f"v2m_ttu_{pid}_q1_norb", {})
        if not nb.get("ok"): continue
        src = "" if f"v2m_eddy_{pid}_normal" in ck else " (normal = no mitigation, timed)"
        L.append(f"| {pid}{src} | {f(nb.get('Vnode_peak_nobd'),1e-3)} | {f(nm.get('frac_first_half'),100)} | {f(nm.get('frac_ch_of_bank'),100)} | {f(nm.get('E_mit_total'),1e3)} | "
                 f"{f(nb.get('Vnode_max_after_quench'),1e-3)} | {f(nb.get('Vnode_min_after_quench'),1e-3)} | {'yes' if nb.get('fires') else 'no'} | {f(nb.get('E_bank_end'),1e3,0)} | {f(nb.get('E_mit_total'),1e3)} | "
                 f"{('yes / ' + f(r12.get('delay'),1e6,2)) if r12.get('fires') else 'no'} | {f(tt.get('Vnode_max_after_quench'),1e-3) if tt.get('ok') else '-'} |")
    # ---- item 2
    L += ["", "## Item 2 - SR3 as NiZn ferrite (stage-1 block: plug starts at 0, no bias, no breakdown)", "",
          "Hold-off fixed at fvs x 0.68 mV.s; A = fvs*0.68e-3/(N*dB_hot); length = A/((OD-ID)/2); Lsat = N^2*2e-7*len*ln(b/a) + 5 nH lead, a = ID/2-2 mm, b = OD/2+8 mm.", "",
          "| material | N | ID/OD [mm] | fvs | Sw [A.us/m] | stack length [mm] | Lsat [nH] | L_static [uH] | R_visc [ohm] | bias [A-turns] | saturates | plug peak [kV] | 10-90 % [ns] | 50-90 % [ns] | plug V when SR3 saturates [kV] |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, d in ck.items():
        if not (k.startswith("v2f2_") and d.get("ok")): continue
        L.append(f"| {d['mat']} | {d['N']} | {d['ID']*1e3:.0f}/{d['OD']*1e3:.0f} | {d['fvs']:g} | {d['Sw']*1e6:g} | {d['length_mm']:.1f} | {d['Lsat_nH']:.0f} | {d['Lstat_uH']:.1f} | {d['Rvisc_ohm']:.0f} | {d['Ibias_At']:.0f} | "
                 f"{'yes' if d['sat'] else 'no'} | {d['Vpk']/1e3:.1f} | {d['edge1090']*1e9:.1f} | {d['edge5090']*1e9:.1f} | {f(d.get('Vplug_at_fire'),1e-3)} |")
    L += ["", "### Full chain (bias, 1 nF block, SRiso, plug at +4 kV), no breakdown", "",
          "| design | Lsat [nH] | gap peak [kV] | 50-90 % [ns] | 10-90 % [ns] | plug V when SR3 saturates [kV] |", "|---|---|---|---|---|---|",
          "| ideal SR3 10 nH (v1) | 10 | -51.1 | - | - | - |"]
    for k, d in ck.items():
        if k.startswith("v2f2fc_") and d.get("ok"):
            L.append(f"| {d['mat']} N={d['N']} {d['ID']*1e3:.0f}/{d['OD']*1e3:.0f} Sw={d['Sw']*1e6:g} | {d['Lsat_nH']:.0f} | {d['Vgap_pk']/1e3:.1f} | {d['edge5090']*1e9:.1f} | {d['edge1090']*1e9:.1f} | {f(d.get('Vplug_at_fire'),1e-3)} |")
    # ---- item 3
    L += ["", "## Item 3 - C_block voltage at the start of each shot [kV] (ideal -4.00) and gap peak of the last shot", "",
          "| inter-shot network | rate | V_Cblock at shot 1..n, then after last | last-shot gap peak (no bd) [kV] | E in R_x during shot [mJ] |", "|---|---|---|---|---|"]
    for k, d in ck.items():
        if not (k.startswith("v2c_") and d.get("ok")): continue
        sh = d["shots"]
        seq = " ".join(f"{s['ic']['V_Cblock']/1e3:+.2f}" for s in sh) + f" -> {sh[-1]['next']['V_Cblock']/1e3:+.2f}"
        L.append(f"| {d['cfg']} | {d['rate']} | {seq} | {sh[-1]['Vnode_peak_nobd']/1e3:.1f} | {sh[-1]['E_Rx_shot']*1e3:.2f} |")
    open(os.path.join(RES, "v2_tables.md"), "w").write("\n".join(L) + "\n")
    return os.path.join(RES, "v2_tables.md")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--items", default="1,2,3"); ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--plots-only", action="store_true"); ap.add_argument("--test", default="")
    A = ap.parse_args()
    if A.fresh and os.path.exists(CK): os.remove(CK)
    ck = load_ck()
    if A.test == "3":
        ic0 = dict(V_C1=0.0, V_C2=0.0, V_C3=0.0, V_Cblock=-4000.0, I_Lsec=0.0)
        met, end, r = shot(ic0, {}, "v2test_shot"); print(met); print(end)
        st, R = recovery(end, 1/150 - r["t"][-1], {}, "v2test_rec"); print(st)
        for tt in np.linspace(0, R["time"][-1], 15):
            i = np.searchsorted(R["time"], tt); print(f"{tt*1e3:6.3f} ms  vx={R['v(x)'][i]:9.1f}  iLsec={R['i(L_sec)'][i]:.4f}")
        sys.exit()
    if A.test == "2":
        core, g = sr3_geom("4C65", 1, 25e-3, 60e-3, 1.0); print(g)
        r = m.run(P(tstop=1.45e-6, tmax=0.01e-9, sr3_model="ferrite", sr3_core=core), "stage1", "v2test_f")
        print(edge_metrics(r["t"], r["v(P)"])); sys.exit()
    if A.test == "1":
        o, r, q = simulate_mit(P(tmax=0.1e-9), "v2test_dd", "diode", dict(Ron=2.0, Cd=2e-12), 1e-6, None)
        print({k: v for k, v in o.items() if not isinstance(v, np.ndarray)})
        sys.exit()
    items = A.items.split(",")
    if "1" in items and not A.plots_only: item1(ck)
    if "2" in items and not A.plots_only: item2(ck)
    if "3" in items and not A.plots_only: item3(ck)
    ck = load_ck()
    print("\n".join(make_plots(ck))); print(make_tables(ck))

