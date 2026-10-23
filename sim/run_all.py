#!/usr/bin/env python3
"""Rev B Plasma Ignition circuit simulation - reproducible driver.

    python3 run_all.py            # everything (ngspice + LTspice/Wine cross-check)
    python3 run_all.py --no-lt    # skip LTspice cross-check
    python3 run_all.py --v2-only  # only the v2 follow-up studies (run_v2.py, resumable)

Outputs: results/*.json|csv|md, plots/*.png. Netlists in netlists/, raw data in out/.
"""
import sys, os, json, math, time, copy, argparse
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import prs_model as m, analysis as a

PLOTS = os.path.join(HERE, "plots"); RES = os.path.join(HERE, "results")
os.makedirs(PLOTS, exist_ok=True); os.makedirs(RES, exist_ok=True)
ap = argparse.ArgumentParser(); ap.add_argument("--no-lt", action="store_true"); ap.add_argument("--no-xyce", action="store_true"); ap.add_argument("--patch", action="store_true")
ap.add_argument("--v2", action="store_true", help="run the v2 follow-up studies (run_v2.py) after v1"); ap.add_argument("--v2-only", action="store_true"); ARGS = ap.parse_args()

def P(**kw):
    p = copy.deepcopy(m.P); p.update(kw); return p

def pct(sim, hand):
    return None if (not isinstance(hand, (int, float))) or hand == 0 or sim is None else 100.0*(sim-hand)/hand

E_S1 = 0.5*m.P["C0a"]*m.P["V0a"]**2
SCAL = lambda d: {k: (float(v) if isinstance(v, (np.floating, float, int)) and not isinstance(v, bool) else v)
                  for k, v in d.items() if not isinstance(v, np.ndarray)}

# =============================================================== 1. block validation
def validate():
    rows = []
    def row(block, qty, hand, sim, unit, note=""):
        rows.append(dict(block=block, quantity=qty, hand=hand, sim=sim, unit=unit,
                         err_pct=pct(sim, hand), note=note))
    # ---- Stage 1 alone (plug starts at 0 V, no bank) with fine time step
    p = P(tstop=1.40e-6, tmax=0.01e-9)
    r = m.run(p, "stage1", "val_stage1")
    t = r["t"]
    def pk(k, lo, hi):
        w = (t > lo) & (t < hi); i = np.argmin(np.where(w, r[k], np.inf)); return t[i], r[k][i]
    def first_min(tt, y, t0, ref):
        i = np.where((tt > t0) & (y < 0.5*ref))[0][0]
        while i+1 < len(y) and y[i+1] <= y[i]: i += 1
        return i
    def stage_metrics(rr):
        tt = rr["t"]; o = {}
        for nm, VS, cap, nxt in (("SR1", p["VS1"], "v(n1)", "v(n2)"), ("SR2", p["VS2"], "v(n2)", "v(n3)"), ("SR3", p["VS3"], "v(n3)", "v(P)")):
            lam = rr[f"v(lam_{nm})"]; k = np.where(lam >= VS)[0]
            if not len(k): o[nm] = None; continue
            tf = tt[k[0]]; vcap = np.interp(tf, tt, rr[cap]); icap = np.argmin(np.where(tt < tf+2e-9, rr[cap], np.inf))
            j = first_min(tt, rr[nxt], tf, vcap); vv = rr[nxt]; w = (tt > tf-5e-9) & (tt <= tt[j])
            t10 = tt[w][np.where(vv[w] < 0.1*vv[j])[0][0]]; t90 = tt[w][np.where(vv[w] < 0.9*vv[j])[0][0]]
            t98 = tt[w][np.where(vv[w] < 0.98*vv[j])[0][0]]
            o[nm] = dict(t_fire=tf, t_cap_peak=tt[icap], v_cap_peak=rr[cap][icap], v_cap_fire=vcap, v_next=vv[j],
                         t_next=tt[j], transfer=(tt[j]-tf), t98=t98-tf, edge1090=t90-t10)
        return o
    sm = stage_metrics(r)
    t1, v1 = sm["SR1"]["t_cap_peak"], sm["SR1"]["v_cap_peak"]
    t2, v2 = sm["SR2"]["t_cap_peak"], sm["SR2"]["v_cap_peak"]
    t3, v3 = sm["SR3"]["t_cap_peak"], sm["SR3"]["v_cap_peak"]
    tP, vP = sm["SR3"]["t_next"], sm["SR3"]["v_next"]
    row("Pulse transformer", "C1 charge time (IGBT on -> C1 peak)", 1.0e-6*1e9, t1*1e9, "ns")
    row("Pulse transformer", "C1 peak voltage", 34.1, -v1/1e3, "kV", "1.1 kV x 31, lossless")
    for nm, hand_t in (("SR1", 200), ("SR2", 40)):
        x = sm[nm]
        row(nm, "transfer time (saturation -> next cap peak)", hand_t, x["transfer"]*1e9, "ns",
            f"fires {(x['t_fire']-x['t_cap_peak'])*1e9:.1f} ns after its cap peak, at {-x['v_cap_fire']/1e3:.1f} kV")
        row(nm, "next-stage peak voltage", 34.1, -x["v_next"]/1e3, "kV")
    x = sm["SR3"]
    row("SR3 (10 nH sat.)", "C3 -> plug transfer to 98 % (10-90 % edge in note)", "2-5", x["t98"]*1e9, "ns",
        f"10-90 % edge {x['edge1090']*1e9:.2f} ns; ideal saturating L, ferrite switching time not modelled; fires {(x['t_fire']-x['t_cap_peak'])*1e9:.2f} ns after C3 peak")
    ring_doc = 2*100/(100+15)
    Cl = 1/(1/p["Cblock"] + 1/(p["Cplug"]+p["Cw"]))
    ring_corr = 2*p["C3"]/(p["C3"]+Cl) * p["Cblock"]/(p["Cblock"]+p["Cplug"]+p["Cw"])
    row("SR3 + plug", "ring-up V_plug/V_C3", ring_doc, vP/x["v_cap_fire"], "x", f"hand incl. 1 nF block + 1.5 pF Cw: {ring_corr:.3f}x")
    row("SR3 + plug", "plug swing (no bias, no breakdown)", 59, -vP/1e3, "kV", "doc: 34 kV x 1.74")
    s1 = dict(t=t, r=r, peaks=(t1, v1, t2, v2, t3, v3, tP, vP))
    p190 = P(tstop=1.40e-6, tmax=0.01e-9, L3s=190e-9)
    r190 = m.run(p190, "stage1", "val_stage1_190n"); x = stage_metrics(r190)["SR3"]
    row("SR3 (190 nH)", "C3 -> plug transfer to 98 %", 5, x["t98"]*1e9, "ns", f"10-90 % edge {x['edge1090']*1e9:.2f} ns; plug {-x['v_next']/1e3:.1f} kV")
    s1["r190"] = r190
    p5u = P(tstop=1.40e-6, tmax=0.01e-9, L3u=5e-6)
    r5u = m.run(p5u, "stage1", "val_stage1_SR3_5uH")
    t_ = r5u["t"]; w = (t_ > 1.0e-6); vv = r5u["v(P)"]
    i = np.argmin(np.where(w, vv, np.inf)); tt = t_[w]; yy = vv[w]
    t10 = a.first_cross(tt, yy, 0.1*vv[i], 0, "down"); t90 = a.first_cross(tt, yy, 0.9*vv[i], 0, "down")
    fired = bool((r5u["v(lam_SR3)"] >= p["VS3"]).any())
    row("SR3 sensitivity (L_unsat 5 uH)", "plug peak", None, -vv[i]/1e3, "kV",
        f"10-90 % edge {(t90-t10)*1e9:.1f} ns; SR3 {'fires' if fired else 'never saturates'}: plug follows C3 through the unsaturated ferrite")
    s1["r5u"] = r5u; s1["edge5u"] = (t90-t10)
    # ---- Stage 2 alone: node pulled to 0 by channel at t=1 ns, bank 4 kV
    st2 = {}
    for flux0, lbl in ((1.5e-3, "spike 1.5 mV.s (doc accounting)"), (0.0, "no spike")):
        q = P(t_bd=1e-9, Rch=1.0, tstop=6e-6, tmax=0.2e-9, flux0=flux0)
        rr = m.run(q, "stage2", f"val_st2_delay_{int(flux0*1e4)}")
        ts = a.first_cross(rr["t"], rr["i(L_iso_air)"], 50.0, 20e-9, "up")
        hand = (q["VSiso"]-flux0)/q["V0b"]
        row("SRiso", f"delay to saturation, {lbl}", hand*1e9, (ts-1e-9)*1e9, "ns",
            "hand = remaining V.s / 4 kV")
        st2[flux0] = rr
    # Z0 / half cycle: R ~ 0
    q = P(t_bd=1e-9, Rch=0.05, tstop=4e-6, tmax=0.2e-9, flux0=1.5e-3, t_close_ramp=5e-9)
    rr = m.run(q, "stage2", "val_st2_Z0")
    iL = rr["i(L_iso_air)"]; tt = rr["t"]
    ts = a.first_cross(tt, iL, 50.0, 20e-9, "up"); ipk = iL.max()
    ti = np.where((tt > ts+20e-9) & (iL < 0.5))[0][0]
    L = q["Lsat"]+q["Lloop"]
    al = q["Rch"]/(2*L); w0 = 1/math.sqrt(L*q["C0b"])
    row("SRiso + C0b", "Z0 = V0*exp(-a*pi/2w0)/Ipk (R=0.05 ohm)", math.sqrt(L/q["C0b"]), q["V0b"]*math.exp(-al*math.pi/(2*w0))/ipk, "ohm",
        "includes core transition at saturation onset")
    row("SRiso + C0b", "half-cycle", math.pi*math.sqrt(L*q["C0b"])*1e9, (tt[ti]-ts)*1e9, "ns",
        "sim measured from 50 A crossing to current zero")
    # first-half-cycle delivery
    deliv = {}
    hand_doc = {0.5: (53, 1.6), 1.0: (78, 1.3), 2.0: (97, 0.9)}
    for R in (0.5, 1.0, 2.0):
        q = P(t_bd=1e-9, Rch=R, tstop=5e-6, tmax=0.2e-9, flux0=1.5e-3)
        rr = m.run(q, "stage2", f"val_st2_R{R}")
        info = dict(t_bd=1e-9)
        mt = a.metrics(q, rr, info)
        # exact series RLC first half cycle (for checking the doc's numbers)
        al = R/(2*L); w0 = 1/math.sqrt(L*q["C0b"]); wd = math.sqrt(w0**2-al**2)
        fr = 1-math.exp(-2*al*math.pi/wd); tpk = math.atan(wd/al)/wd
        ipk_ex = q["V0b"]/(wd*L)*math.exp(-al*tpk)*math.sin(wd*tpk)
        row("Stage 2 delivery", f"first half-cycle energy, R={R} ohm", hand_doc[R][0], 100*mt["frac_first_half"], "%",
            f"exact RLC: {100*fr:.1f} %")
        row("Stage 2 delivery", f"peak current, R={R} ohm", hand_doc[R][1], mt["Ipk_first"]/1e3, "kA",
            f"exact RLC: {ipk_ex/1e3:.2f} kA")
        deliv[R] = (rr, mt, 100*fr, ipk_ex)
    return rows, s1, st2, deliv

# =============================================================== 2/3. full chain sweeps
def case(tag, tq=None, rebreak=True, **kw):
    kw = dict(kw); tmax = kw.pop("tmax", 0.1e-9)
    p = P(tmax=tmax, **kw)
    t0 = time.time()
    try:
        info, r, q = a.simulate(p, tag, tq_rel=tq, rebreak=rebreak)
        ok, err = True, ""
    except Exception as e:
        info, r, q, ok, err = {}, None, p, False, str(e)[-400:]
    d = dict(tag=tag, ok=ok, err=err, runtime_s=time.time()-t0, tq=tq, rebreak=rebreak,
             **{k: kw[k] for k in kw}, **SCAL(info))
    d.setdefault("model", p["model"]); d.setdefault("Rch", p["Rch"]); d.setdefault("C0b", p["C0b"])
    d.setdefault("Vbd", p["Vbd"]); d.setdefault("simulator", p.get("simulator", "ngspice"))
    with open(os.path.join(RES, "checkpoint.jsonl"), "a") as f: f.write(json.dumps(d, default=str) + "\n")
    print(f"  {tag:42s} ok={ok} delay={d.get('delay')} {d['runtime_s']:.1f}s {err[:120]}", flush=True)
    return d, r, info

def patch():
    """Re-run validation + the cases fixed after the first full run; merge into results.json; regenerate
    tables and the plots that do not need full-chain waveforms (01, 02, 08)."""
    J = json.load(open(os.path.join(RES, "results.json")))
    rows, s1, st2, deliv = validate()
    res = J["results"]
    def put(d):
        nonlocal res
        res = [x for x in res if x["tag"] != d["tag"]] + [d]
    base = [x for x in res if x["tag"] == "base_bd27k5_C625_R1.0"][0]
    basep = [x for x in res if x["tag"] == "base_bdpeak_C625_R1.0"][0]
    for ref, lbl, Vbd in ((base, "sim spike, bd 27.5 kV", 27.5e3), (basep, "sim spike, bd at peak", "peak"), (None, "doc 1.2 mV.s", 27.5e3)):
        sv = ref["lam_spike"] if ref else 1.2e-3
        for sgn in (-1, +1):
            tag = f"jit_{lbl.split(',')[0].replace(' ','')}{'_pk' if Vbd=='peak' else ''}_{'+' if sgn>0 else '-'}20"
            d, r, info = case(tag, Vbd=Vbd, VSiso=m.P["VSiso"]-sgn*0.2*sv); d["jit_ref"] = lbl; d["jit_dVs"] = sgn*0.2*sv; put(d)
    d, r, info = case("sens_SR1SR2_LuLs_300", unsat_ratio12=300.0, tmax=0.05e-9); d["sens"] = "SR1/SR2 Lu/Ls 300"; put(d)
    J.update(validation=rows, results=res)
    json.dump(J, open(os.path.join(RES, "results.json"), "w"), indent=1, default=str)
    make_plots(rows, s1, st2, deliv, res, {}, only=(1, 2, 8))
    make_tables(rows, res)

def main():
    if ARGS.patch:
        return patch()
    T0 = time.time()
    print("== 1. block validation"); rows, s1, st2, deliv = validate()
    results = []; waves = {}
    print("== 2/3. full chain: baseline")
    for Vbd in (27.5e3, "peak"):
        for C0b in (62.5e-9, 125e-9):
            for R in (0.5, 1.0, 2.0):
                tag = f"base_{'bd27k5' if Vbd != 'peak' else 'bdpeak'}_C{int(C0b*1e10)}_R{R}"
                d, r, info = case(tag, Vbd=Vbd, C0b=C0b, Rch=R); results.append(d)
                if C0b == 62.5e-9: waves[tag] = (r, info)
    print("== quench")
    for Vbd in (27.5e3, "peak"):
        for R in ((0.5, 1.0, 2.0) if Vbd != "peak" else (1.0,)):
            for tq in (0.5e-6, 1.0e-6, 1.5e-6):
                for rb in (True, False):
                    tag = f"quench_{'bd27k5' if Vbd != 'peak' else 'bdpeak'}_R{R}_tq{tq*1e6:.1f}_{'rb' if rb else 'norb'}"
                    d, r, info = case(tag, tq=tq, rebreak=rb, Vbd=Vbd, Rch=R); results.append(d)
                    if R == 1.0 and Vbd != "peak": waves[tag] = (r, info)
    print("== temperature / available flux swing")
    N, Ae = m.P["N"], m.P["Ae"]
    for lbl, dB in (("design 1.98 T", 1.979), ("120C conservative 2.26 T", 2.26), ("120C catalog 2.38 T", 2.38), ("20C 2.46 T", 2.46)):
        for Vbd in (27.5e3, "peak"):
            tag = f"dB_{dB:.2f}_{'bd27k5' if Vbd != 'peak' else 'bdpeak'}"
            d, r, info = case(tag, Vbd=Vbd, VSiso=N*Ae*dB); d["dB_label"] = lbl; d["dB"] = dB; results.append(d)
    print("== spike V.s jitter (+/-20 %)")
    base = [x for x in results if x["tag"] == "base_bd27k5_C625_R1.0"][0]
    basep = [x for x in results if x["tag"] == "base_bdpeak_C625_R1.0"][0]
    for ref, lbl, Vbd in ((base, "sim spike, bd 27.5 kV", 27.5e3), (basep, "sim spike, bd at peak", "peak"), (None, "doc 1.2 mV.s", 27.5e3)):
        sv = ref["lam_spike"] if ref else 1.2e-3
        for sgn in (-1, +1):
            tag = f"jit_{lbl.split(',')[0].replace(' ','')}{'_pk' if Vbd=='peak' else ''}_{'+' if sgn>0 else '-'}20"
            # +/-20 % spike V.s == -/+ the same V.s on the remaining SRiso budget (core cannot start below -Bs)
            d, r, info = case(tag, Vbd=Vbd, VSiso=m.P["VSiso"]-sgn*0.2*sv); d["jit_ref"] = lbl; d["jit_dVs"] = sgn*0.2*sv; results.append(d)
    print("== sensitivities")
    for kw, lbl in ((dict(ke=2.25e-5), "eddy ke x0.5"), (dict(ke=9e-5), "eddy ke x2"),
                    (dict(Cw=3e-12), "Cw 3 pF"), (dict(Cw=3e-12, Vbd="peak"), "Cw 3 pF, bd at peak"),
                    (dict(Cw=1.5e-12, Vbd="peak"), "Cw 1.5 pF, bd at peak"),
                    (dict(L3u=5e-6), "SR3 L_unsat 5 uH"), (dict(L3s=190e-9), "SR3 L_sat 190 nH"),
                    (dict(unsat_ratio12=300.0, tmax=0.05e-9), "SR1/SR2 Lu/Ls 300")):
        tag = "sens_" + lbl.replace(" ", "_").replace("/", "").replace(",", "")
        d, r, info = case(tag, **kw); d["sens"] = lbl; results.append(d)
    print("== core-model comparison (eddy vs TTU port vs LTspice TTU)")
    cmp_cases = [(R, Vbd) for R in (0.5, 1.0, 2.0) for Vbd in (27.5e3, "peak")]
    for model, sim, extra in (("ttu", "ngspice", {}), ("ttu", "ngspice", {"ttu_latch": False}), ("ttu_lt", "ltspice", {})):
        if sim == "ltspice" and ARGS.no_lt: continue
        for R, Vbd in cmp_cases:
            tag = f"cmp_{model}{'' if extra.get('ttu_latch', True) else '_nolatch'}_{'bd27k5' if Vbd != 'peak' else 'bdpeak'}_R{R}"
            d, r, info = case(tag, model=model, simulator=sim, Rch=R, Vbd=Vbd, **extra)
            d["model_label"] = {"ttu": "TTU port (ngspice)", "ttu_lt": "TTU original (LTspice/Wine)"}[model] + ("" if extra.get("ttu_latch", True) else ", no rate latch")
            results.append(d)
            if R == 1.0 and Vbd == 27.5e3: waves[tag] = (r, info)
        for tq, rb in ((1.0e-6, True), (1.0e-6, False)):
            tag = f"cmp_{model}{'' if extra.get('ttu_latch', True) else '_nolatch'}_quench1.0_{'rb' if rb else 'norb'}"
            d, r, info = case(tag, tq=tq, rebreak=rb, model=model, simulator=sim, **extra)
            d["model_label"] = {"ttu": "TTU port (ngspice)", "ttu_lt": "TTU original (LTspice/Wine)"}[model] + ("" if extra.get("ttu_latch", True) else ", no rate latch")
            results.append(d)
    if not ARGS.no_xyce:
        print("== Xyce Jiles-Atherton cross-check (stage-2 block)")
        import subprocess; subprocess.run([sys.executable, os.path.join(HERE, "xyce_ja.py")], check=False)
    json.dump(dict(validation=rows, results=results, E_stage1=E_S1, runtime_s=time.time()-T0),
              open(os.path.join(RES, "results.json"), "w"), indent=1, default=str)
    make_plots(rows, s1, st2, deliv, results, waves)
    make_tables(rows, results)
    print(f"done in {time.time()-T0:.0f} s")

# =============================================================== plots
def make_plots(rows, s1, st2, deliv, results, waves, only=None):
    want = lambda k: only is None or k in only
    if want(1):
        # stage 1 waveforms
        t, r = s1["t"], s1["r"]
        fig, ax = plt.subplots(1, 2, figsize=(13, 4.5))
        for k, lb in (("v(n1)", "C1"), ("v(n2)", "C2"), ("v(n3)", "C3"), ("v(P)", "plug (no breakdown)")):
            ax[0].plot(t*1e6, r[k]/1e3, label=lb); 
        ax[0].set_xlim(0, 1.32); ax[0].set_xlabel("t [us]"); ax[0].set_ylabel("kV"); ax[0].grid(); ax[0].legend()
        ax[0].set_title("Stage 1 alone: transformer -> SR1 -> SR2 -> SR3 -> plug")
        t3 = s1["peaks"][4]
        for rr, lb in ((r, "SR3 10 nH (ideal)"), (s1["r190"], "SR3 190 nH"), (s1["r5u"], "SR3 L_unsat 5 uH")):
            ax[1].plot((rr["t"]-t3)*1e9, rr["v(P)"]/1e3, label="plug, " + lb)
        ax[1].plot((t-t3)*1e9, r["v(n3)"]/1e3, "k--", label="C3 (10 nH case)")
        ax[1].set_xlim(-60, 40); ax[1].set_xlabel("t - t(C3 peak) [ns]"); ax[1].grid(); ax[1].legend(fontsize=8)
        ax[1].set_title("Plug edge (stage 1 alone, plug starts at 0 V)")
        fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "01_stage1_validation.png"), dpi=110); plt.close(fig)
    if want(2):
        # stage 2 delivery block
        fig, ax = plt.subplots(1, 2, figsize=(13, 4.5))
        for R, (rr, mt, fr, ipk) in deliv.items():
            ax[0].plot(rr["t"]*1e6, rr["i(L_iso_air)"]/1e3, label=f"R={R} ohm")
            ax[1].plot(rr["t"]*1e6, rr["v(bk)"]/1e3, label=f"R={R} ohm")
        ax[0].set_title("Stage 2 alone: SRiso current (spike flux 1.5 mV.s preset)"); ax[0].set_ylabel("kA")
        ax[1].set_title("C0b voltage (reversal)"); ax[1].set_ylabel("kV")
        for x in ax: x.grid(); x.legend(); x.set_xlabel("t [us]")
        fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "02_stage2_block_validation.png"), dpi=110); plt.close(fig)
    if want(3):
        # full-chain plug node + SRiso voltage over the delay, R = 0.5/1/2, two breakdown points
        fig, axs = plt.subplots(2, 2, figsize=(14, 8), sharex="col")
        for j, bd in enumerate(("bd27k5", "bdpeak")):
            for R in (0.5, 1.0, 2.0):
                key = f"base_{bd}_C625_R{R}"
                if key not in waves or waves[key][0] is None: continue
                rr, info = waves[key]; tb = info["t_bd"]
                axs[0, j].plot((rr["t"]-tb)*1e6, rr["v(P)"]/1e3, label=f"R={R}", lw=0.8)
                axs[1, j].plot((rr["t"]-tb)*1e6, (rr["v(bk)"]-rr["v(P)"])/1e3, label=f"R={R}", lw=0.8)
            axs[0, j].set_ylim(-3, 5); axs[1, j].set_ylim(-3, 6)
            axs[0, j].set_title(f"plug node, breakdown {'27.5 kV (rising edge)' if bd=='bd27k5' else 'at peak (about -51 kV)'}")
            axs[1, j].set_title("voltage across SRiso (bank - node)")
            axs[1, j].set_xlabel("t - t_breakdown [us]"); axs[1, j].set_xlim(-0.05, 4)
            for x in axs[:, j]: x.grid(); x.legend(); x.set_ylabel("kV")
        fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "03_fullchain_node_and_SRiso_delay.png"), dpi=110); plt.close(fig)
    if want(4):
        # full chain stage-2 current and bank
        fig, ax = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
        for R in (0.5, 1.0, 2.0):
            key = f"base_bd27k5_C625_R{R}"
            if key not in waves or waves[key][0] is None: continue
            rr, info = waves[key]; tb = info["t_bd"]
            ax[0].plot((rr["t"]-tb)*1e6, rr["i(L_iso_air)"]/1e3, label=f"R={R}", lw=0.9)
            ax[1].plot((rr["t"]-tb)*1e6, rr["v(bk)"]/1e3, label=f"R={R}", lw=0.9)
        ax[0].set_ylabel("SRiso current [kA]"); ax[1].set_ylabel("C0b [kV]"); ax[1].set_xlabel("t - t_breakdown [us]")
        ax[0].set_title("Full chain, 62.5 nF, breakdown 27.5 kV: stage-2 current and bank\n(second half-cycle at 0.5 and 1 ohm; none at 2 ohm within 13 us)")
        for x in ax: x.grid(); x.legend()
        fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "04_fullchain_stage2_current_bank.png"), dpi=110); plt.close(fig)
    if want(5):
        # quench cases
        fig, ax = plt.subplots(3, 2, figsize=(14, 10), sharex=True)
        for j, rb in enumerate(("rb", "norb")):
            for tq in (0.5, 1.0, 1.5):
                key = f"quench_bd27k5_R1.0_tq{tq:.1f}_{rb}"
                if key not in waves or waves[key][0] is None: continue
                rr, info = waves[key]; tb = info["t_bd"]; x = (rr["t"]-tb)*1e6
                ax[0, j].plot(x, rr["v(P)"]/1e3, label=f"quench at +{tq} us", lw=0.8)
                ax[1, j].plot(x, (rr["v(bk)"]-rr["v(P)"])/1e3, lw=0.8)
                ax[2, j].plot(x, (rr["v(lam_iso)"])*1e3, lw=0.8)
            rr, info = waves["base_bd27k5_C625_R1.0"]; x = (rr["t"]-info["t_bd"])*1e6
            ax[0, j].plot(x, rr["v(P)"]/1e3, "k:", label="no quench", lw=0.8)
            ax[1, j].plot(x, (rr["v(bk)"]-rr["v(P)"])/1e3, "k:", lw=0.8)
            ax[2, j].plot(x, rr["v(lam_iso)"]*1e3, "k:", lw=0.8)
            ax[2, j].axhline(m.P["VSiso"]*1e3, color="r", ls="--", lw=0.7)
            ax[0, j].set_title("Quench, hot-channel re-break at |V| > 2.1 kV" if rb == "rb" else "Quench, no re-break (channel cold)")
            ax[0, j].set_ylim(-18, 18); ax[1, j].set_ylim(-16, 16)
            ax[0, j].set_ylabel("plug node [kV]"); ax[1, j].set_ylabel("V across SRiso [kV]"); ax[2, j].set_ylabel("SRiso flux [mV.s]")
            ax[2, j].set_xlabel("t - t_breakdown [us]"); ax[2, j].set_xlim(-0.1, 6)
            for a_ in ax[:, j]: a_.grid()
            ax[0, j].legend(fontsize=8)
        fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "05_quench_cases.png"), dpi=110); plt.close(fig)
    if want(6):
        # core model comparison waveform
        fig, ax = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
        for key, lb, st in (("base_bd27k5_C625_R1.0", "square-loop + eddy (ngspice, primary)", "-"),
                            ("cmp_ttu_bd27k5_R1.0", "TTU port (ngspice)", "--"),
                            ("cmp_ttu_nolatch_bd27k5_R1.0", "TTU port, no rate latch", "-."),
                            ("cmp_ttu_lt_bd27k5_R1.0", "TTU original (LTspice/Wine)", ":")):
            if key not in waves or waves[key][0] is None: continue
            rr, info = waves[key]; x = (rr["t"]-info["t_bd"])*1e6
            ax[0].plot(x, rr["i(L_iso_air)"]/1e3, st, label=lb); ax[1].plot(x, rr["v(lam_iso)"]*1e3, st, label=lb)
        ax[0].set_ylabel("SRiso current [kA]"); ax[1].set_ylabel("SRiso flux [mV.s]"); ax[1].set_xlabel("t - t_breakdown [us]")
        ax[0].set_title("SRiso core-model comparison, R = 1 ohm, 62.5 nF, breakdown 27.5 kV")
        for x in ax: x.grid(); x.legend(fontsize=8)
        fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "06_core_model_comparison.png"), dpi=110); plt.close(fig)
    if want(7):
        # summary charts
        fig, ax = plt.subplots(1, 3, figsize=(16, 4.5))
        for bd, mk in (("bd27k5", "o"), ("bdpeak", "s")):
            for C0b, col in ((625, "C0"), (1250, "C1")):
                xs, ys, ys2 = [], [], []
                for R in (0.5, 1.0, 2.0):
                    d = [x for x in results if x["tag"] == f"base_{bd}_C{C0b}_R{R}"]
                    if d and d[0]["ok"] and d[0].get("frac_first_half") is not None:
                        xs.append(R); ys.append(100*d[0]["frac_first_half"]); ys2.append(d[0]["Ipk"]/1e3)
                ax[0].plot(xs, ys, mk+"-", color=col, label=f"{'62.5' if C0b==625 else '125'} nF, {'bd 27.5 kV' if bd=='bd27k5' else 'bd at peak'}")
                ax[1].plot(xs, ys2, mk+"-", color=col)
        ax[0].plot([0.5, 1, 2], [53, 78, 97], "k*", ms=12, label="doc hand (62.5 nF)")
        ax[1].plot([0.5, 1, 2], [1.6, 1.3, 0.9], "k*", ms=12, label="doc hand (62.5 nF)")
        ax[0].set_xlabel("channel R [ohm]"); ax[0].set_ylabel("first half-cycle delivery [%]"); ax[0].legend(fontsize=7)
        ax[1].set_xlabel("channel R [ohm]"); ax[1].set_ylabel("peak current [kA]"); ax[1].legend(fontsize=7)
        # delay bar chart
        labs, vals = [], []
        for tag, lb in (("base_bd27k5_C625_R1.0", "no quench\nbd 27.5k"), ("base_bdpeak_C625_R1.0", "no quench\nbd peak"),
                        ("quench_bd27k5_R1.0_tq0.5_rb", "quench 0.5\nre-break"), ("quench_bd27k5_R1.0_tq1.5_rb", "quench 1.5\nre-break"),
                        ("quench_bd27k5_R1.0_tq0.5_norb", "quench 0.5\nno re-break"), ("quench_bd27k5_R1.0_tq1.5_norb", "quench 1.5\nno re-break")):
            d = [x for x in results if x["tag"] == tag]
            labs.append(lb); vals.append((d[0].get("delay") or np.nan)*1e6 if d else np.nan)
        b = ax[2].bar(range(len(vals)), [v if np.isfinite(v) else 0 for v in vals],
                      color=["C0" if np.isfinite(v) else "r" for v in vals])
        for i, v in enumerate(vals):
            ax[2].text(i, (v if np.isfinite(v) else 0)+0.05, f"{v:.2f}" if np.isfinite(v) else "no fire\n(13 us)", ha="center", fontsize=8)
        ax[2].axhline(2.0, color="k", ls="--", lw=0.8); ax[2].set_xticks(range(len(vals))); ax[2].set_xticklabels(labs, fontsize=7)
        ax[2].set_ylabel("breakdown -> SRiso saturation [us]"); ax[2].set_title("Stage 2 delay (R = 1 ohm)")
        for x in ax[:2]: x.grid()
        fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "07_summary_delivery_delay.png"), dpi=110); plt.close(fig)
    if want(8):
        # jitter + dB
        fig, ax = plt.subplots(1, 2, figsize=(13, 5.0))
        dd = [x for x in results if x["tag"].startswith("dB_") and x["ok"]]
        for bd, mk in (("bd27k5", "o-"), ("bdpeak", "s-")):
            s = sorted([x for x in dd if x["tag"].endswith(bd)], key=lambda x: x["dB"])
            ax[0].plot([x["dB"] for x in s], [x["delay"]*1e6 for x in s], mk, label="bd 27.5 kV" if bd == "bd27k5" else "bd at peak")
        ax[0].set_xlabel("available forward swing dB [T]"); ax[0].set_ylabel("delay [us]"); ax[0].grid(); ax[0].legend()
        ax[0].set_title("Delay vs core flux swing (1.98 design / 2.26-2.38 at 120 C / 2.46 at 20 C)")
        jj = [x for x in results if x["tag"].startswith("jit_") and x["ok"]]
        labs = [f"{x['jit_ref']}\n{x['jit_dVs']*1e3:+.3f} mV.s" for x in jj]
        ref = {"sim spike, bd 27.5 kV": "base_bd27k5_C625_R1.0", "doc 1.2 mV.s": "base_bd27k5_C625_R1.0", "sim spike, bd at peak": "base_bdpeak_C625_R1.0"}
        vals = [(x["delay"] - [y for y in results if y["tag"] == ref[x["jit_ref"]]][0]["delay"])*1e9 for x in jj]
        ax[1].bar(range(len(vals)), vals); ax[1].set_xticks(range(len(vals)))
        ax[1].set_xticklabels(labs, fontsize=7, rotation=30, ha="right")
        ax[1].set_ylabel("delay change [ns]"); ax[1].set_title("+/-20 % spike V.s jitter"); ax[1].grid()
        fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "08_jitter_and_flux_swing.png"), dpi=110); plt.close(fig)

# =============================================================== tables
def fmt(v, nd=3):
    if v is None: return "-"
    if isinstance(v, str): return v
    if isinstance(v, float) and not math.isfinite(v): return "-"
    return f"{v:.{nd}g}"

def make_tables(rows, results):
    L = ["# Auto-generated tables (run_all.py)", "", "## Block validation", "",
         "| Block | Quantity | Hand (doc) | Sim | Unit | Error % | Note |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['block']} | {r['quantity']} | {fmt(r['hand'])} | {fmt(r['sim'])} | {r['unit']} | {fmt(r['err_pct'],2)} | {r['note']} |")
    L += ["", "## Full-chain runs", "",
          "| tag | ok | model | Vbd | R | C0b nF | quench +us | re-break | t_rebreak-t_q ns | spike V.s mV.s | delay us | node max in delay V | Viso min in delay V | 1st half % | Ipk kA | C0b reversal % | E_ch total mJ | E_ch stage-1 mJ | spike->branch peak mJ (% of 58) | Cw peak mJ | core eddy spike mJ | lam end mV.s |",
          "|" + "---|"*22]
    for d in results:
        rbt = (d.get("t_rebreak") - d["t_bd"] - d["tq"])*1e9 if d.get("t_rebreak") and d.get("tq") else None
        L.append("| " + " | ".join([d["tag"], str(d["ok"]), d.get("model_label", d.get("model", "")), fmt(d.get("Vbd")), fmt(d.get("Rch")),
                 fmt(d.get("C0b", 0)*1e9), fmt(d["tq"]*1e6 if d.get("tq") else None), str(d.get("rebreak")) if d.get("tq") else "-",
                 fmt(rbt), fmt(d.get("lam_spike", 0)*1e3 if d.get("lam_spike") is not None else None),
                 fmt(d["delay"]*1e6 if d.get("delay") else None, 4), fmt(d.get("Vnode_delay_max")), fmt(d.get("Viso_delay_min")),
                 fmt(100*d["frac_first_half"] if d.get("frac_first_half") else None), fmt(d["Ipk"]/1e3 if d.get("Ipk") else None),
                 fmt(100*d["reversal"] if d.get("reversal") else None), fmt(d["E_ch_total"]*1e3 if d.get("E_ch_total") else None),
                 fmt(d["E_ch_stage1"]*1e3 if d.get("E_ch_stage1") else None),
                 (f"{d['E_branch_spike_peak']*1e3:.2f} ({100*d['E_branch_spike_peak']/E_S1:.1f} %)" if d.get("E_branch_spike_peak") is not None else "-"),
                 fmt(d["E_Cw_peak"]*1e3 if d.get("E_Cw_peak") is not None else None), fmt(d["E_core_spike"]*1e3 if d.get("E_core_spike") is not None else None),
                 fmt(d["lam_end"]*1e3 if d.get("lam_end") is not None else None)]) + " |")
    open(os.path.join(RES, "tables.md"), "w").write("\n".join(L) + "\n")
    import csv
    keys = sorted({k for d in results for k in d})
    with open(os.path.join(RES, "results.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); [w.writerow(d) for d in results]

if __name__ == "__main__":
    if not ARGS.v2_only:
        main()
    if ARGS.v2 or ARGS.v2_only:     # v2 follow-up (quench mitigations, SR3 ferrite, C_block recovery); resumable
        import subprocess
        subprocess.run([sys.executable, os.path.join(HERE, "run_v2.py")], check=True)
