"""Run LTspice (Windows build under Wine, headless batch) and parse ASCII .raw output."""
import os, subprocess, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
LTEXE = os.path.join(HERE, "ltspice", "app", "LTspice", "LTspice.exe")
WDIR = os.path.join(HERE, "ltspice", "runs")
os.makedirs(WDIR, exist_ok=True)

def parse_ascii_raw(fn):
    data = open(fn, "rb").read()
    try:
        txt = data.decode("utf-16-le") if data[1:2] == b"\x00" else data.decode("latin-1")
    except UnicodeDecodeError:
        txt = data.decode("latin-1")
    lines = txt.splitlines()
    nvar = npts = None; names = []; i = 0
    while i < len(lines):
        L = lines[i]
        if L.startswith("No. Variables:"): nvar = int(L.split(":")[1])
        elif L.startswith("No. Points:"): npts = int(L.split(":")[1])
        elif L.startswith("Variables:"):
            for j in range(nvar):
                names.append(lines[i+1+j].split()[1]); 
            i += nvar
        elif L.startswith("Values:"):
            i += 1; break
        i += 1
    vals = []
    tok = " ".join(lines[i:]).split()
    # format: idx v0 v1 ... per point
    arr = []
    k = 0
    for p in range(npts):
        k += 1  # index
        arr.append([float(x) for x in tok[k:k+nvar]]); k += nvar
    arr = np.array(arr)
    return {n.lower(): np.abs(arr[:, j]) if n.lower() == "time" else arr[:, j] for j, n in enumerate(names)}

def run(netlist_text, tag, timeout=900):
    cir = os.path.join(WDIR, tag + ".cir")
    with open(cir, "w") as f: f.write(netlist_text)
    env = dict(os.environ, WINEPREFIX=os.path.expanduser("~/.wine-ltspice"), WINEDEBUG="-all")
    if "DISPLAY" not in env: env["DISPLAY"] = ":77"
    r = subprocess.run(["wine", LTEXE, "-b", "-ascii", tag + ".cir"], cwd=WDIR, env=env,
                       capture_output=True, text=True, timeout=timeout)
    raw = os.path.join(WDIR, tag + ".raw"); log = os.path.join(WDIR, tag + ".log")
    logtxt = ""
    if os.path.exists(log):
        b = open(log, "rb").read()
        logtxt = b.decode("utf-16-le", "ignore") if b[1:2] == b"\x00" else b.decode("latin-1")
    if not os.path.exists(raw) or os.path.getmtime(raw) < os.path.getmtime(cir):
        raise RuntimeError(f"LTspice produced no raw for {tag}\n{logtxt[-1500:]}")
    return parse_ascii_raw(raw), logtxt
