"""Multi-pass case runner + metric extraction for the Rev B PRS model."""
import numpy as np, prs_model as m

def cumtrapz(y, t):
    out = np.zeros_like(y); out[1:] = np.cumsum(0.5*(y[1:]+y[:-1])*np.diff(t)); return out

def first_cross(t, y, thr, after=0.0, direction="down"):
    idx = np.where(t >= after)[0]
    if len(idx) == 0: return None
    yy = y[idx]
    hit = np.where(yy <= thr)[0] if direction == "down" else np.where(yy >= thr)[0]
    if len(hit) == 0: return None
    k = idx[hit[0]]
    if k == 0: return t[0]
    # linear interp
    t0, t1, y0, y1 = t[k-1], t[k], y[k-1], y[k]
    return t0 + (thr-y0)*(t1-t0)/(y1-y0) if y1 != y0 else t1

def find_breakdown(p, tag):
    q = dict(p); q.update(t_bd=None, t_quench=None, t_rebreak=None, tstop=1.6e-6)
    r = m.run(q, "full", tag+"_p1")
    t, v = r["t"], r["v(P)"]
    vmin_i = np.argmin(v[t < 1.5e-6]); vpk = v[vmin_i]
    info = dict(Vnode_peak_nobd=vpk, t_peak_nobd=t[vmin_i])
    if p["Vbd"] == "peak" or (-p["Vbd"] < vpk):
        info["bd_mode"] = "peak" if p["Vbd"] == "peak" else f"threshold {p['Vbd']/1e3:.1f} kV NOT reached -> closed at peak"
        info["t_bd"] = t[vmin_i]
    else:
        info["bd_mode"] = f"threshold {p['Vbd']/1e3:.1f} kV"
        info["t_bd"] = first_cross(t, v, -p["Vbd"], 0.5e-6, "down")
    return info, r

def simulate(p, tag, tq_rel=None, rebreak=True, t_after=13e-6):
    info, r1 = find_breakdown(p, tag)
    q = dict(p); q["t_bd"] = info["t_bd"]; q["tstop"] = info["t_bd"] + t_after
    q["t_quench"] = None if tq_rel is None else info["t_bd"] + tq_rel
    r = m.run(q, "full", tag)
    if tq_rel is not None and rebreak:
        trb = first_cross(r["t"], np.abs(r["v(P)"]), p["V_rebreak"], q["t_quench"] + 2e-9, "up")
        info["t_rebreak"] = trb
        if trb is not None:
            q["t_rebreak"] = trb
            r = m.run(q, "full", tag)
    info.update(metrics(q, r, info))
    return info, r, q

def metrics(q, r, info):
    t = r["t"]; vP = r["v(P)"]; vb = r["v(bk)"]
    g = r["v(chg)"]
    ich = vP*(g/q["Rch"] + 1/q["Roff"])
    Pch = vP*ich
    Ech = cumtrapz(Pch, t)
    iL = r["i(L_iso_air)"]; icw = r["i(V_iso_cw)"]
    Ib = iL + icw                      # bank-branch current, bk -> P
    Pbr = vP*(-Ib)                     # power from node into the SRiso/C0b branch
    Ebr = cumtrapz(Pbr, t)
    lam = r["v(lam_iso)"] + q["flux0"]
    tbd = info["t_bd"]
    out = {}
    N, Ae = q["N"], q["Ae"]
    # spike window: from SR3 firing (node leaves +4 kV) to breakdown + 30 ns
    t_sp0 = first_cross(t, vP, q["V0b"]-2e3, 0.9e-6, "down")
    i_sp1 = np.searchsorted(t, tbd + 30e-9)
    i_sp0 = np.searchsorted(t, t_sp0)
    out["t_spike_start"] = t_sp0
    out["lam_spike"] = lam[i_sp1]                    # V.s used by the spike (incl. pre-spike leakage)
    out["lam_at_bd"] = lam[np.searchsorted(t, tbd)]
    out["E_branch_spike_peak"] = np.max(Ebr[i_sp0:i_sp1+1]) - Ebr[i_sp0]
    out["E_branch_spike_net"] = Ebr[i_sp1] - Ebr[i_sp0]
    out["Vnode_min"] = vP[i_sp0:i_sp1+1].min()
    out["Viso_max_spike"] = (vb - vP)[i_sp0:i_sp1+1].max()
    # SRiso saturation: forward flux reaches budget, iso current > 50 A after the spike
    after = tbd + 60e-9
    tsat = first_cross(t, iL, 50.0, after, "up")
    out["t_sat"] = tsat
    out["delay"] = None if tsat is None else tsat - tbd
    E0 = 0.5*q["C0b"]*q["V0b"]**2
    out["E_bank0"] = E0
    if tsat is not None:
        i0 = np.searchsorted(t, tsat)
        # end of first half cycle: SRiso current returns through ~0
        k = np.where((t > tsat + 20e-9) & (iL < 0.5))[0]
        i1 = k[0] if len(k) else len(t)-1
        Ebank_sat = 0.5*q["C0b"]*vb[i0]**2
        out["Vbank_at_sat"] = vb[i0]
        out["E_ch_first_half"] = Ech[i1] - Ech[i0]
        out["frac_first_half"] = out["E_ch_first_half"]/Ebank_sat
        out["t_half"] = t[i1]-t[i0]
        out["Ipk"] = np.max(np.abs(iL[i0:]))
        out["Ipk_first"] = np.max(iL[i0:i1+1])
        out["Vbank_rev_min"] = vb[i0:].min()
        out["reversal"] = -vb[i0:].min()/q["V0b"]
        out["E_ch_stage2_total"] = Ech[-1] - Ech[i0]
        out["E_bank_end"] = 0.5*q["C0b"]*vb[-1]**2
        out["lam_max"] = lam.max()
        # second (reverse) saturation
        k2 = np.where((t > t[i1]) & (iL < -50))[0]
        out["t_second_sat"] = (t[k2[0]] - tbd) if len(k2) else None
    out["E_ch_total"] = Ech[-1]
    out["E_ch_stage1"] = Ech[np.searchsorted(t, tsat)] if tsat else Ech[-1]
    # node behaviour during the delay window
    w = (t > tbd + 30e-9) & (t < ((tsat - 50e-9) if tsat else t[-1]))
    out["Vnode_delay_max"] = vP[w].max() if w.any() else None
    out["Viso_delay_min"] = (vb - vP)[w].min() if w.any() else None
    out["lam_end"] = lam[-1]
    out["Iiso_delay_max"] = iL[w].max() if w.any() else None
    # spike energy split (window t_sp0 .. tbd+30ns)
    viso = vb - vP; vcore = r["v(iso_m)"] - vP
    sl = slice(i_sp0, i_sp1+1)
    out["E_Cw_peak"] = np.max(0.5*q["Cw"]*viso[sl]**2)
    out["E_core_spike"] = (cumtrapz(vcore*iL, t)[i_sp1] - cumtrapz(vcore*iL, t)[i_sp0])
    out["dVbank_spike"] = vb[i_sp1] - vb[i_sp0]
    # low-current re-break: channel current after re-break until saturation
    if info.get("t_rebreak") is not None and tsat is not None:
        w2 = (t > info["t_rebreak"] + 50e-9) & (t < tsat - 50e-9)
        if w2.any():
            out["Ich_after_rebreak_median"] = float(np.median(np.abs(ich[w2])))
            out["Ich_after_rebreak_max"] = float(np.max(np.abs(ich[w2])))
    out["ich"] = ich; out["Ech"] = Ech; out["Ebr"] = Ebr
    return out
