"""Xyce 7.9 Jiles-Atherton (MutIndNonLin CORE) cross-check of the SRiso / stage-2 block.
Bias winding (N=1, ideal DC current source) resets the core before the shot; the channel closes at t_bd."""
import os, subprocess, json, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
XY = os.path.join(HERE, "xyce", "install", "bin", "Xyce"); RD = os.path.join(HERE, "xyce", "runs")
JA = dict(MS=7.2e5, A=4, K=3, C=0.05, ALPHA=3.5e-6)   # mu0*Ms = 0.905 T; run B peaks near 0.95 T. Bs ~1.19 T would need Ms ~9.47e5, which this run did not use.
TBD = 150e-6

def run(R=1.0, C0b=62.5e-9, Hbias=-60.0, tq=None, trb=None, tag="ja", tend=12e-6):
    Ib = Hbias*0.22/1.0
    L0 = 4e-7*np.pi*36*8e-4/0.22
    Lair = 0.27e-6 - L0
    pts = f"0 0 {TBD:.9e} 0 {TBD+10e-9:.9e} 1"
    if tq is not None:
        pts += f" {TBD+tq:.9e} 1 {TBD+tq+1e-9:.9e} 0"
        if trb is not None: pts += f" {trb:.9e} 0 {trb+1e-9:.9e} 1"
    net = f"""* Xyce JA stage-2 block {tag}
C0b bk 0 {C0b} IC=4000
Lair bk m {Lair:.6e}
L1 m P 6
L2 bb 0 1
K1 L1 L2 1.0 KMOD
.model KMOD CORE (MS={JA['MS']} A={JA['A']} K={JA['K']} C={JA['C']} ALPHA={JA['ALPHA']} AREA=8 PATH=22 GAP=0)
Ibias 0 bb PWL(0 0 100u {Ib} 1 {Ib})
Cw bk P 1.5p
Cplug P 0 15p IC=4000
Vg g 0 PWL({pts})
Bch P 0 I={{V(P)*(V(g)/{R} + 1e-9)}}
.options timeint method=gear reltol=1e-3
.options nonlin maxstep=200 maxsearchstep=4
.tran 1n {TBD+tend:.6e} 0 1n uic
.print tran format=csv V(bk) V(P) V(m) I(L1) V(g)
.end
"""
    fn = os.path.join(RD, tag + ".cir"); open(fn, "w").write(net)
    r = subprocess.run([XY, fn], capture_output=True, text=True, cwd=RD, timeout=3000)
    open(os.path.join(RD, tag + ".log"), "w").write(r.stdout + r.stderr)
    d = np.genfromtxt(fn + ".csv", delimiter=",", names=True)
    return d

def metrics(d, R, C0b):
    t = d["TIME"]; vb = d["VBK"]; vP = d["VP"]; vm = d["VM"]; i = d["IL1"]; g = d["VG"]
    w = t >= TBD - 1e-9
    lam = np.concatenate([[0], np.cumsum(0.5*((vm-vP)[1:]+(vm-vP)[:-1])*np.diff(t))])
    B = lam/(6*8e-4); Bb = B[np.searchsorted(t, TBD)]
    sgn = 1.0 if i[w].max() > -i[w].min() else -1.0
    i = sgn*i
    k = np.where((t > TBD+20e-9) & (i > 50))[0]
    out = dict(R=R, C0b=C0b, B_at_bias=float(Bb), dB_avail_used=float(B[w].max()-Bb))
    if len(k) == 0:
        out.update(delay=None, Vnode_max_after=float(vP[t > TBD+20e-9].max()), lam_end_T=float(B[-1]-Bb)); return out
    ts = t[k[0]]; i0 = k[0]
    k1 = np.where((t > ts+20e-9) & (i < 0.5))[0]
    if len(k1) == 0:
        out.update(delay=float(ts-TBD), note="SRiso saturated but no current zero (channel open)", Ipk=float(i[i0:].max()),
                   Vnode_max_after=float(vP[t > TBD+20e-9].max())); return out
    i1 = k1[0]
    ich = vP*(g/R + 1e-9); P = vP*ich
    E = np.concatenate([[0], np.cumsum(0.5*(P[1:]+P[:-1])*np.diff(t))])
    Eb = 0.5*C0b*vb[i0]**2
    out.update(delay=float(ts-TBD), frac_first_half=float((E[i1]-E[i0])/Eb), Ipk=float(i[i0:].max()),
               reversal=float(-vb[i0:].min()/4000), E_ch_total=float(E[-1]-E[np.searchsorted(t, TBD)]),
               Imag_delay_median=float(np.median(i[(t > TBD+50e-9) & (t < ts-50e-9)])))
    return out

if __name__ == "__main__":
    res = []
    for R in (0.5, 1.0, 2.0):
        for C0b in (62.5e-9,):
            d = run(R, C0b, tag=f"ja_R{R}"); m = metrics(d, R, C0b); print(m, flush=True); res.append(m)
    # quench at +1 us, no re-break
    d = run(1.0, tq=1e-6, tag="ja_q1_norb"); m = metrics(d, 1.0, 62.5e-9); m["case"] = "quench +1us no re-break"
    t = d["TIME"]; vP = d["VP"]; w = t > TBD+1e-6
    m["Vnode_max_after_quench"] = float(vP[w].max())
    k = np.where(w & (np.abs(vP) > 2100))[0]; m["t_cross_2k1_after_quench_ns"] = float((t[k[0]]-TBD-1e-6)*1e9) if len(k) else None
    print(m, flush=True); res.append(m)
    if len(k):
        d = run(1.0, tq=1e-6, trb=t[k[0]], tag="ja_q1_rb"); m2 = metrics(d, 1.0, 62.5e-9); m2["case"] = "quench +1us, re-break 2.1 kV"
        print(m2, flush=True); res.append(m2)
    json.dump(dict(JA=JA, results=res), open(os.path.join(HERE, "results", "xyce_ja.json"), "w"), indent=1)
