#!/usr/bin/env python3
"""Rev C — design-out by margin.

Sizes SR3, SRiso and the stage-2 re-strike voltage against the Rev B topology.
Does not add circuit blocks. Every run is checkpointed under results/revc/.

    python3 run_revc.py
"""
import os, sys, json, math, time, copy
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import prs_model as m
import analysis as a

RES = os.path.join(HERE, "results", "revc")
PLOT = os.path.join(HERE, "plots", "revc")
os.makedirs(RES, exist_ok=True)
os.makedirs(PLOT, exist_ok=True)
CK = os.path.join(RES, "checkpoint.jsonl")
MU0 = m.MU0

# Rev B numbers (PRS_RevB_architecture_proposal.md and prs_model.P).
REV_B = dict(m.P)
VS_SR3_REQ = 0.68e-3          # 34 kV x 40 ns x 1/2
E_BANK_B = 0.5 * REV_B["C0b"] * REV_B["V0b"] ** 2   # 0.5 J
# "Enough" for the engine: the proposal's 1 ohm hand delivery, 78% of 0.5 J.
E_ENOUGH = 0.78 * E_BANK_B

# Lossy SR1/SR2 from run_v2.py. Lair is the Rev B transfer inductance.
SR1_CORE = dict(N=100, A=17e-3 / (100 * 2.0), le=0.20, dB=2.0, Hc=2.5, ke=4.5e-5, mui=5e4, Lair=81e-6)
SR2_CORE = dict(N=40, A=3.4e-3 / (40 * 2.0), le=0.15, dB=2.0, Hc=2.5, ke=4.5e-5, mui=5e4, Lair=3.2e-6)


def scal(o):
    if isinstance(o, dict):
        return {k: scal(v) for k, v in o.items() if not isinstance(v, np.ndarray)}
    if isinstance(o, (np.floating, np.integer)):
        return float(o)
    if isinstance(o, tuple):
        return [scal(v) for v in o]
    return o


def load_ck():
    D = {}
    if os.path.exists(CK):
        for line in open(CK):
            try:
                d = json.loads(line)
                D[d["tag"]] = d
            except Exception:
                pass
    return D


def save_ck(d):
    with open(CK, "a") as f:
        f.write(json.dumps(scal(d), default=str) + "\n")


def pct(sim, ref):
    if ref == 0:
        return 0.0 if sim == 0 else float("inf")
    return 100.0 * (sim - ref) / ref


def audit_row(name, ref, sim, unit=""):
    dp = pct(sim, ref)
    flag = abs(dp) > 5.0
    return dict(name=name, rev_b=ref, simulated=sim, pct=dp, unit=unit, flag=flag)


# -------------------------------------------------------------------------- SR3 geometry
def coax_Lsat(N, A, ID, OD, lead=5e-9, ins_in=2e-3, ins_out=8e-3):
    hw = (OD - ID) / 2
    length = A / hw
    a = ID / 2 - ins_in
    b = OD / 2 + ins_out
    if a <= 0 or b <= a:
        raise ValueError("insulation does not fit this coax")
    L = N * N * 2e-7 * length * math.log(b / a) + lead
    return L, length, math.log(b / a)


def leak_bound(H, dB, ID, OD, VS=VS_SR3_REQ, ins_in=2e-3, ins_out=8e-3):
    """I_leak * Lsat lower bound. N and stack length cancel. See Rev B report s.9.2, corrected."""
    le = math.pi * (ID + OD) / 2
    hw = (OD - ID) / 2
    a = ID / 2 - ins_in
    b = OD / 2 + ins_out
    return (MU0 / (2 * math.pi)) * H * (VS / dB) * (le / hw) * math.log(b / a)


def H_hold(dB, mu, Sw, Hc, tau=40e-9):
    """H at full swing: static loop + switching term + coercivity. Bias margin is separate."""
    return dB / (MU0 * mu) + Sw / tau + Hc


def sr3_core(N, ID, OD, dB, mu, Sw, Hc, fvs):
    A = fvs * VS_SR3_REQ / (N * dB)
    Lair, length, lnba = coax_Lsat(N, A, ID, OD)
    ke = Sw / dB
    le = math.pi * (ID + OD) / 2
    core = dict(N=N, A=A, le=le, dB=dB, Hc=Hc, ke=ke, mui=mu, Lair=Lair)
    Hbias = dB / 2 / (MU0 * mu) + Hc + 300.0
    meta = dict(N=N, ID=ID, OD=OD, dB=dB, mu=mu, Sw=Sw, Hc=Hc, fvs=fvs,
                A_m2=A, A_cm2=A * 1e4, length_mm=length * 1e3, Lsat_nH=Lair * 1e9,
                VS=N * A * dB, le=le, Ibias_At=Hbias * le, ln_ba=lnba)
    return core, meta


def edge_metrics(t, v, t_from=0.9e-6, t_to=1.5e-6):
    w = (t > t_from) & (t < t_to)
    idx = np.where(w)[0]
    if len(idx) < 5:
        return dict(Vpk=float("nan"), edge1090=float("nan"), edge5090=float("nan"))
    i0 = idx[np.argmin(v[idx])]
    vpk = float(v[i0])
    if vpk >= 0:
        return dict(Vpk=vpk, edge1090=float("nan"), edge5090=float("nan"), t_pk=float(t[i0]))
    j = i0
    while j > idx[0] and v[j] < 0.9 * vpk:
        j -= 1
    t90 = t[j]
    while j > idx[0] and v[j] < 0.1 * vpk:
        j -= 1
    t10 = t[j]
    j = i0
    while j > idx[0] and v[j] < 0.5 * vpk:
        j -= 1
    t50 = t[j]
    return dict(Vpk=vpk, t_pk=float(t[i0]), edge1090=float(t90 - t10), edge5090=float(t90 - t50))


def stage2_delivery(p, tag):
    """Stage-2 block only. Channel already closed. Returns first-half and 10 us energies."""
    q = dict(p)
    q.update(t_bd=1e-9, Rch=1.0, tstop=14e-6, tmax=0.25e-9, flux0=1.5e-3,
             t_quench=None, t_rebreak=None)
    r = m.run(q, "stage2", tag)
    t = r["t"]
    iL = r["i(L_iso_air)"]
    vP = r["v(P)"]
    vb = r["v(bk)"]
    g = r["v(chg)"]
    ich = vP * (g / q["Rch"] + 1.0 / q["Roff"])
    Ech = a.cumtrapz(vP * ich, t)
    ts = a.first_cross(t, iL, 50.0, 20e-9, "up")
    out = dict(t_sat=ts, E_bank0=0.5 * q["C0b"] * q["V0b"] ** 2, V0b=q["V0b"], C0b=q["C0b"],
               model=q["model"], Ae=q["Ae"], Lsat=q["Lsat"], VSiso=q["VSiso"])
    if ts is None:
        out.update(frac_first=None, E_first=None, E_10us=None, Ipk=float(np.max(np.abs(iL))),
                   reversal=None, delay=None)
        return out, r
    k = np.where((t > ts + 20e-9) & (iL < 0.5))[0]
    i1 = int(k[0]) if len(k) else len(t) - 1
    i0 = int(np.searchsorted(t, ts))
    i10 = int(np.searchsorted(t, ts + 10e-6))
    Ebank_sat = 0.5 * q["C0b"] * vb[i0] ** 2
    E_first = float(Ech[i1] - Ech[i0])
    out.update(delay=float(ts - 1e-9),
               frac_first=E_first / Ebank_sat,
               E_first=E_first,
               E_10us=float(Ech[min(i10, len(t) - 1)] - Ech[i0]),
               Ipk=float(np.max(iL[i0:])),
               Ipk_first=float(np.max(iL[i0:i1 + 1])),
               Vrev=float(vb[i0:].min()),
               reversal=float(-vb[i0:].min() / q["V0b"]),
               Ebank_sat=float(Ebank_sat))
    return out, r


# -------------------------------------------------------------------------- GX120 re-strike bracket
def gx120_restrike():
    """HAND ESTIMATE. Cold breakdown from the handover Paschen fit, then a hot-channel bracket."""
    Bmm, Smm = 60.0, 42.0
    Vd = math.pi * (Bmm / 2) ** 2 * Smm / 1000.0          # cc
    CR = 8.5
    Vc = Vd / (CR - 1)
    r = Smm / 2
    Lr = 3.5
    n = 1.30
    Tin, Pin = 320.0, 0.95
    T0, P0 = 293.15, 1.0

    def V_cc(theta_deg):
        th = math.radians(theta_deg)
        x = r * ((1 - math.cos(th)) + (math.sin(th) ** 2) / (2 * Lr))
        return Vc + math.pi * (Bmm / 2) ** 2 * x / 1000.0

    Vbdc = Vd + Vc
    out = dict(Vd_cc=Vd, Vc_cc=Vc, formula="V(kV)=24.22*δd+6.08*sqrt(δd)", gap_mm=0.75, d_cm=0.075)
    rows = []
    for theta in (25.0, 20.0):
        Vf = V_cc(theta)
        rv = Vbdc / Vf
        Pf = Pin * rv ** n
        Tf = Tin * rv ** (n - 1)
        delta = (Pf / P0) * (T0 / Tf)
        x = delta * 0.075
        Vair = 24.22 * x + 6.08 * math.sqrt(x)
        Vmix = 1.1 * Vair
        rows.append(dict(theta_btdc=theta, V_cc=Vf, rv=rv, P_atm=Pf, T_K=Tf, delta=delta,
                         Vair_kV=Vair, Vmix_kV=Vmix))
    out["cold"] = rows
    # Design cold number: 25 deg BTDC, mixture x1.1. Stock GX120 magneto timing.
    cold = rows[0]
    Vcold = cold["Vmix_kV"] * 1e3
    Tfire = cold["T_K"]
    # Channel temperature at ~2 us. Bracket, not a GX120 measurement.
    # Best (easiest re-strike): 8000 K core. Worst: 2500 K, cooled at firing pressure.
    brackets = []
    for name, Tch, f_att, note in (
        ("best", 8000.0, 1.0, "hot core still near arc temperature at 2 us"),
        ("revB_method_on_GX120", 4000.0, 1.0, "4000 K held to 2 us (Wang-class persistence, applied at firing T not 300 K)"),
        ("worst", 2500.0, 1.2, "cooled kernel at firing pressure, plus x1.2 for O2/H2O attachment"),
    ):
        V = Vcold * (Tfire / Tch) * f_att
        brackets.append(dict(end=name, T_channel_K=Tch, f_attach=f_att, V_rebreak_V=V, note=note))
    out["brackets"] = brackets
    out["V_cold_V"] = Vcold
    out["T_fire_K"] = Tfire
    return out


def main():
    ck = load_ck()
    waves = {}
    audit = []

    def remember(tag, d, wave=None):
        d = scal(d)
        d["tag"] = tag
        save_ck(d)
        ck[tag] = d
        if wave is not None:
            np.savez(os.path.join(RES, tag + ".npz"), **{k: np.asarray(v) for k, v in wave.items()})
        return d

    # ===================================================================== 0. validation
    print("== validation ==", flush=True)
    # component identity on an unmodified run
    for k, unit in (("V0a", "V"), ("C0a", "F"), ("n", ""), ("C1", "F"), ("C2", "F"), ("C3", "F"),
                    ("L1s", "H"), ("L2s", "H"), ("VS1", "V.s"), ("VS2", "V.s"), ("VS3", "V.s"),
                    ("L3s", "H"), ("Cblock", "F"), ("Cplug", "F"), ("V0b", "V"), ("C0b", "F"),
                    ("N", ""), ("Ae", "m2"), ("VSiso", "V.s"), ("Lsat", "H"), ("Lloop", "H"),
                    ("Cw", "F"), ("V_rebreak", "V")):
        audit.append(audit_row(k, REV_B[k], REV_B[k], unit))

    # ideal stage-1 plug peak
    tag = "revc_s1_ideal"
    if tag not in ck:
        p = copy.deepcopy(m.P)
        p.update(tstop=1.45e-6, tmax=0.05e-9)
        t0 = time.time()
        r = m.run(p, "stage1", tag)
        e = edge_metrics(r["t"], r["v(P)"])
        remember(tag, dict(ok=True, study="validation", runtime_s=time.time() - t0, **e,
                           note="ideal SR3, stage-1 block, Rev B values"),
                 dict(t=r["t"], vP=r["v(P)"], v3=r["v(n3)"]))
        print(f"  {tag} Vpk={e['Vpk']/1e3:.2f} kV edge10-90={e['edge1090']*1e9:.2f} ns", flush=True)
    waves["ideal"] = np.load(os.path.join(RES, tag + ".npz"))

    tag = "revc_full_ideal"
    if tag not in ck:
        p = copy.deepcopy(m.P)
        p.update(tstop=1.55e-6, tmax=0.05e-9)
        t0 = time.time()
        r = m.run(p, "full", tag)
        e = edge_metrics(r["t"], r["v(P)"] - p["V0b"])
        remember(tag, dict(ok=True, study="validation", runtime_s=time.time() - t0,
                           Vgap=float(r["v(P)"].min()), **e,
                           note="ideal SR1/SR2/SR3, full chain, no breakdown"),
                 dict(t=r["t"], vP=r["v(P)"]))
        print(f"  {tag} Vgap={r['v(P)'].min()/1e3:.2f} kV", flush=True)

    tag = "revc_full_lossy12"
    if tag not in ck:
        p = copy.deepcopy(m.P)
        p.update(tstop=1.55e-6, tmax=0.05e-9, sr12_model="lossy", sr1_core=SR1_CORE, sr2_core=SR2_CORE)
        t0 = time.time()
        try:
            r = m.run(p, "full", tag)
            e = edge_metrics(r["t"], r["v(P)"] - p["V0b"])
            remember(tag, dict(ok=True, study="validation", runtime_s=time.time() - t0,
                               Vgap=float(r["v(P)"].min()), **e,
                               note="lossy SR1/SR2, ideal SR3, full chain, no breakdown"),
                     dict(t=r["t"], vP=r["v(P)"]))
            print(f"  {tag} Vgap={r['v(P)'].min()/1e3:.2f} kV", flush=True)
        except Exception as ex:
            remember(tag, dict(ok=False, study="validation", err=str(ex)[-400:]))
            print("  lossy12 FAILED", ex)

    for model in ("eddy", "ttu"):
        tag = f"revc_st2_{model}_base"
        if tag not in ck:
            p = copy.deepcopy(m.P)
            p["model"] = model
            t0 = time.time()
            o, r = stage2_delivery(p, tag)
            o.update(ok=True, study="validation", runtime_s=time.time() - t0, sized=False)
            remember(tag, o, dict(t=r["t"], vP=r["v(P)"], vbk=r["v(bk)"], iL=r["i(L_iso_air)"],
                                  Ech=a.cumtrapz(r["v(P)"] * r["v(P)"] * (r["v(chg)"] / p["Rch"]), r["t"])))
            print(f"  {tag} frac={o.get('frac_first')} E10={o.get('E_10us')} Ipk={o.get('Ipk_first')}", flush=True)

    # ===================================================================== 1. SR3
    print("== SR3 ==", flush=True)
    # Corners. Sources are written into the note; this is the numerical bracket.
    corners = {
        # worst stacks the bad ends: low mu (4C65 datasheet floor), high Sw, low hot dB
        "worst": dict(mu=100.0, Sw=40e-6, dB=0.55, Hc=200.0, T_C=120.0),
        # best: datasheet ceiling mu, lower Sw, 25 C swing
        "best": dict(mu=150.0, Sw=10e-6, dB=0.64, Hc=200.0, T_C=25.0),
    }
    ID, OD = 25e-3, 60e-3
    # Corrected leakage bound at the report's 25/80 mm, 190 nH reference (should be ~47 A, not 25 A).
    H_ref = H_hold(0.60, 125.0, 20e-6, 200.0)
    K_ref = leak_bound(H_ref, 0.60, 25e-3, 80e-3)
    I_at_190 = K_ref / 190e-9
    print(f"  leakage-bound check 25/80 mm 4C65: I(190 nH) = {I_at_190:.1f} A", flush=True)

    # Size on the worst corner. Smallest N whose stack is 4-20 mm and whose bound is <= 20 A.
    worst = corners["worst"]
    H_w = H_hold(worst["dB"], worst["mu"], worst["Sw"], worst["Hc"])
    candidates = []
    for fvs in (1.15, 1.30, 1.50):
        for N in range(4, 81, 2):
            core, meta = sr3_core(N, ID, OD, worst["dB"], worst["mu"], worst["Sw"], worst["Hc"], fvs)
            if not (4.0 <= meta["length_mm"] <= 20.0):
                continue
            # Bound uses the REQUIRED volt-seconds (what the charge applies), at full worst-case H.
            K = leak_bound(H_w, worst["dB"], ID, OD)
            Ibound = K / meta["Lsat_nH"] * 1e9
            candidates.append((Ibound, N, fvs, meta, core))
    candidates.sort(key=lambda z: (z[0], z[1]))
    ok = [z for z in candidates if z[0] <= 20.0]
    # Smallest turn count that gets the bound under 20 A. If none do, take the lowest bound and flag it.
    pool = sorted(ok, key=lambda z: (z[1], z[2])) if ok else candidates
    Ibound, N_sel, fvs_sel, meta_w, core_w = pool[0]
    holdoff_bound_met = bool(ok)
    print(f"  chosen N={N_sel} fvs={fvs_sel} Lsat={meta_w['Lsat_nH']:.0f} nH "
          f"len={meta_w['length_mm']:.1f} mm Ibound={Ibound:.1f} A", flush=True)

    # Same copper and iron at the best corner: dB and mu and Sw change, area is fixed by the worst-case size.
    # Area was set with worst dB, so best dB gives more volt-seconds on the same iron.
    A_fixed = core_w["A"]
    def core_at(corner_name):
        c = corners[corner_name]
        # Rebuild Lair from the FIXED area (hardware does not change with temperature).
        Lair, length, lnba = coax_Lsat(N_sel, A_fixed, ID, OD)
        ke = c["Sw"] / c["dB"]
        le = math.pi * (ID + OD) / 2
        core = dict(N=N_sel, A=A_fixed, le=le, dB=c["dB"], Hc=c["Hc"], ke=ke, mui=c["mu"], Lair=Lair)
        Hbias = c["dB"] / 2 / (MU0 * c["mu"]) + c["Hc"] + 300.0
        meta = dict(corner=corner_name, N=N_sel, ID=ID, OD=OD, dB=c["dB"], mu=c["mu"], Sw=c["Sw"],
                    Hc=c["Hc"], fvs_worst_size=fvs_sel, A_cm2=A_fixed * 1e4, length_mm=length * 1e3,
                    Lsat_nH=Lair * 1e9, VS=N_sel * A_fixed * c["dB"], le=le, Ibias_At=Hbias * le,
                    T_C=c["T_C"])
        return core, meta

    sr3_results = {}
    for corner in ("worst", "best"):
        core, meta = core_at(corner)
        for chain, blocks, tstop in (("s1", "stage1", 1.45e-6), ("full", "full", 1.55e-6)):
            tag = f"revc_sr3_{corner}_{chain}"
            if tag in ck and ck[tag].get("ok"):
                sr3_results[tag] = ck[tag]
                continue
            p = copy.deepcopy(m.P)
            p.update(tstop=tstop, tmax=0.02e-9, sr3_model="ferrite", sr3_core=core)
            t0 = time.time()
            try:
                r = m.run(p, blocks, tag)
                sig = r["v(P)"] if blocks == "stage1" else r["v(P)"] - p["V0b"]
                e = edge_metrics(r["t"], sig)
                VS = core["N"] * core["A"] * core["dB"]
                lam = r["v(lam_SR3)"]
                sat = bool((lam >= 0.98 * VS).any())
                d = dict(ok=True, study="sr3", chain=chain, runtime_s=time.time() - t0, sat=sat,
                         lam_max=float(lam.max()),
                         margin_vs_req=float(lam.max()) / VS_SR3_REQ - 1.0 if False else VS / VS_SR3_REQ - 1.0,
                         V_C3=float(r["v(n3)"].min()) if "v(n3)" in r else None,
                         Vgap=float(r["v(P)"].min()), **meta, **e)
                remember(tag, d, dict(t=r["t"], vP=r["v(P)"], v3=r["v(n3)"], lam=lam))
                print(f"  {tag} sat={sat} Vpk={e['Vpk']/1e3:.1f} edge={e['edge1090']*1e9:.1f} ns "
                      f"Vgap={d['Vgap']/1e3:.1f}", flush=True)
            except Exception as ex:
                remember(tag, dict(ok=False, study="sr3", chain=chain, err=str(ex)[-400:], **meta))
                print(f"  {tag} FAILED {ex}")
            sr3_results[tag] = ck[tag]

    # one lossy-SR1/SR2 full chain at the worst SR3, to put the gap next to the -40 kV correction
    tag = "revc_sr3_worst_full_lossy12"
    if tag not in ck:
        core, meta = core_at("worst")
        p = copy.deepcopy(m.P)
        p.update(tstop=1.55e-6, tmax=0.02e-9, sr3_model="ferrite", sr3_core=core,
                 sr12_model="lossy", sr1_core=SR1_CORE, sr2_core=SR2_CORE)
        t0 = time.time()
        try:
            r = m.run(p, "full", tag)
            e = edge_metrics(r["t"], r["v(P)"] - p["V0b"])
            remember(tag, dict(ok=True, study="sr3", runtime_s=time.time() - t0,
                               Vgap=float(r["v(P)"].min()), **e, **meta,
                               note="lossy SR1/SR2 + worst SR3"),
                     dict(t=r["t"], vP=r["v(P)"]))
            print(f"  {tag} Vgap={r['v(P)'].min()/1e3:.1f}", flush=True)
        except Exception as ex:
            remember(tag, dict(ok=False, study="sr3", err=str(ex)[-400:]))
            print("  lossy+worst SR3 FAILED", str(ex)[-200:])

    # flags for the chosen SR3 versus Rev B ideal SR3
    audit.append(audit_row("SR3_N", 1.0, N_sel, "turns"))
    audit.append(audit_row("SR3_Lsat", REV_B["L3s"], core_at("worst")[0]["Lair"], "H"))
    audit.append(audit_row("SR3_VS_worst", VS_SR3_REQ, core_at("worst")[1]["VS"], "V.s"))

    # ===================================================================== 3. re-strike hand estimate (before SRiso resize)
    print("== re-strike bracket ==", flush=True)
    rb = gx120_restrike()
    V_worst = max(b["V_rebreak_V"] for b in rb["brackets"] if b["end"] == "worst")
    V_best_rb = min(b["V_rebreak_V"] for b in rb["brackets"] if b["end"] == "best")
    # 1.5x at the worst end, and never below the Rev B 4 kV (that would be a relaxation, not a margin).
    V_bank = max(REV_B["V0b"], 1.5 * V_worst)
    print(f"  V_rebreak best={V_best_rb:.0f} worst={V_worst:.0f} -> V_bank={V_bank:.0f}", flush=True)

    def sriso_scaled(V, C):
        """Same N=6, dB=2.0 T. Delay volt-seconds = V * 2 us. Spike budget stays 1.5 mV.s."""
        VS = 1.5e-3 + V * 2e-6
        Ae = VS / (6.0 * 2.0)
        Lsat = REV_B["Lsat"] * (Ae / REV_B["Ae"])
        return dict(V0b=V, C0b=C, VSiso=VS, Ae=Ae, Lsat=Lsat)

    # ===================================================================== 2. SRiso sizing on the pessimistic model
    print("== SRiso ==", flush=True)
    # Start from 0.5 J at the chosen voltage (C changes if V changed), then grow C until TTU clears E_ENOUGH.
    C_try = 2 * E_BANK_B / V_bank ** 2
    sized = None
    for attempt in range(4):
        sc = sriso_scaled(V_bank, C_try)
        for model in ("ttu", "eddy"):
            tag = f"revc_st2_{model}_a{attempt}"
            if tag not in ck:
                p = copy.deepcopy(m.P)
                p.update(model=model, **sc)
                t0 = time.time()
                o, r = stage2_delivery(p, tag)
                o.update(ok=True, study="sriso", attempt=attempt, runtime_s=time.time() - t0, sized=True)
                remember(tag, o, dict(t=r["t"], vbk=r["v(bk)"], iL=r["i(L_iso_air)"],
                                      Ech=a.cumtrapz(r["v(P)"] ** 2 * (r["v(chg)"] / 1.0), r["t"])))
                print(f"  {tag} E10={o.get('E_10us')} frac={o.get('frac_first')} C={C_try:.3e}", flush=True)
        E10 = ck[f"revc_st2_ttu_a{attempt}"].get("E_10us") or 0.0
        sized = dict(attempt=attempt, **sc, E10_ttu=E10, E10_eddy=ck[f"revc_st2_eddy_a{attempt}"].get("E_10us"))
        if E10 >= E_ENOUGH * 1.15:
            break
        # grow C, keep V. 10% overshoot so the next run is not on the knife edge.
        scale = (E_ENOUGH / E10) * 1.10 if E10 > 0 else 1.5
        C_try *= scale
    sized["clears"] = (sized["E10_ttu"] or 0) >= E_ENOUGH

    audit.append(audit_row("V0b_sized", REV_B["V0b"], sized["V0b"], "V"))
    audit.append(audit_row("C0b_sized", REV_B["C0b"], sized["C0b"], "F"))
    audit.append(audit_row("VSiso_sized", REV_B["VSiso"], sized["VSiso"], "V.s"))
    audit.append(audit_row("Ae_sized", REV_B["Ae"], sized["Ae"], "m2"))
    audit.append(audit_row("Lsat_sized", REV_B["Lsat"], sized["Lsat"], "H"))

    # ===================================================================== re-strike circuit, no clamp
    print("== re-strike circuit ==", flush=True)
    # Quench 1 us after breakdown. No diode clamp in the netlist.
    for label, Vrb, use_sized in (
        ("base4kV_worst", V_worst, False),
        ("base4kV_best", V_best_rb, False),
        ("sized_worst", V_worst, True),
        ("sized_best", V_best_rb, True),
    ):
        tag = f"revc_rb_{label}"
        if tag in ck and "ok" in ck[tag]:
            continue
        p = copy.deepcopy(m.P)
        p["V_rebreak"] = Vrb
        if use_sized:
            p.update(sriso_scaled(sized["V0b"], sized["C0b"]))
        t0 = time.time()
        try:
            info, r, q = a.simulate(p, tag, tq_rel=1.0e-6, rebreak=True, t_after=8e-6)
            flat = {k: v for k, v in info.items() if not isinstance(v, np.ndarray)}
            flat.update(ok=True, study="restrike", label=label, V_rebreak=Vrb, sized=use_sized,
                        runtime_s=time.time() - t0, V0b=p["V0b"], C0b=p["C0b"])
            remember(tag, flat, dict(t=r["t"], vP=r["v(P)"], vbk=r["v(bk)"]))
            print(f"  {tag} rebreak={flat.get('t_rebreak')} delay={flat.get('delay')} "
                  f"rev={flat.get('reversal')}", flush=True)
        except Exception as ex:
            remember(tag, dict(ok=False, study="restrike", label=label, err=str(ex)[-500:],
                               runtime_s=time.time() - t0))
            print(f"  {tag} FAILED", str(ex)[-180:])

    # ===================================================================== plots
    print("== plots ==", flush=True)
    # 1. SR3 edge, stage-1 block
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for key, lab, style in (
        ("revc_s1_ideal", "Rev B ideal SR3", dict(color="0.45", lw=1.2)),
        ("revc_sr3_worst_s1", "Sized SR3, worst corner", dict(color="tab:red", lw=1.6)),
        ("revc_sr3_best_s1", "Sized SR3, best corner", dict(color="tab:blue", lw=1.4)),
    ):
        z = np.load(os.path.join(RES, key + ".npz"))
        t = z["t"] * 1e6
        msk = (z["t"] > 0.9e-6) & (z["t"] < 1.45e-6)
        ax.plot(t[msk], z["vP"][msk] / 1e3, label=lab, **style)
    ax.set_xlabel("time (µs)")
    ax.set_ylabel("plug node (kV)")
    ax.set_title("SR3 stage-1 edge: Rev B ideal vs sized corners")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT, "revc_sr3_edge.png"), dpi=140)
    plt.close()

    # 2. SRiso energy
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    series = [
        ("revc_st2_eddy_base", "eddy, Rev B 4 kV / 62.5 nF", "tab:green"),
        ("revc_st2_ttu_base", "TTU, Rev B", "tab:orange"),
        (f"revc_st2_ttu_a{sized['attempt']}", "TTU, sized bank", "tab:red"),
        (f"revc_st2_eddy_a{sized['attempt']}", "eddy, sized bank", "tab:blue"),
    ]
    for tag, lab, col in series:
        zp = os.path.join(RES, tag + ".npz")
        if not os.path.exists(zp):
            continue
        z = np.load(zp)
        ax.plot(z["t"] * 1e6, z["Ech"] * 1e3, label=lab, color=col, lw=1.5)
    ax.axhline(E_ENOUGH * 1e3, color="k", ls="--", lw=0.8, label=f"enough ({E_ENOUGH*1e3:.0f} mJ)")
    ax.set_xlabel("time from stage-2 release (µs)")
    ax.set_ylabel("channel energy (mJ)")
    ax.set_title("SRiso delivery, R = 1 Ω, no clamp")
    ax.set_xlim(0, 12)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT, "revc_sriso_energy.png"), dpi=140)
    plt.close()

    # 3. re-strike node
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for tag, lab, col in (
        ("revc_rb_base4kV_worst", "4 kV bank, worst re-break threshold", "tab:orange"),
        ("revc_rb_sized_worst", "sized bank, worst re-break threshold", "tab:red"),
        ("revc_rb_sized_best", "sized bank, best re-break threshold", "tab:blue"),
    ):
        zp = os.path.join(RES, tag + ".npz")
        if not os.path.exists(zp):
            continue
        z = np.load(zp)
        ax.plot(z["t"] * 1e6, z["vP"] / 1e3, label=lab, color=col, lw=1.3)
    ax.axhline(V_worst / 1e3, color="tab:red", ls="--", lw=0.8, label=f"worst re-break {V_worst/1e3:.1f} kV")
    ax.axhline(-V_worst / 1e3, color="tab:red", ls=":", lw=0.7)
    ax.set_xlabel("time (µs)")
    ax.set_ylabel("plug node (kV)")
    ax.set_title("Re-strike after a 1 µs quench — no diode clamp")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT, "revc_restrike_node.png"), dpi=140)
    plt.close()

    # dump tables
    summary = dict(
        I_leak_bound_25x80_190nH_A=I_at_190,
        sr3=dict(N=N_sel, fvs=fvs_sel, ID_mm=ID * 1e3, OD_mm=OD * 1e3,
                 Ibound_A=Ibound, holdoff_bound_met=holdoff_bound_met, worst=core_at("worst")[1], best=core_at("best")[1],
                 corners=corners),
        restrike=rb,
        V_bank=V_bank,
        V_rebreak_worst=V_worst,
        V_rebreak_best=V_best_rb,
        E_enough=E_ENOUGH,
        E_bank_revB=E_BANK_B,
        sized=sized,
        audit=audit,
    )
    # pull live checkpoint rows
    summary["runs"] = {k: v for k, v in load_ck().items() if str(k).startswith("revc_")}
    with open(os.path.join(RES, "revc_summary.json"), "w") as f:
        json.dump(scal(summary), f, indent=2, default=str)
    print("wrote", os.path.join(RES, "revc_summary.json"))
    print("SR3", N_sel, fvs_sel, "Vbank", V_bank, "sized", sized)


if __name__ == "__main__":
    main()
