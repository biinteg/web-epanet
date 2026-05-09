# solver.py
import wntr
from epyt import epanet

def clean_inp_file(path):
    """Menghapus tag yang menyebabkan Error 201 pada WNTR"""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    with open(path, "w", encoding="utf-8") as f:
        skip = False
        for line in lines:
            u = line.strip().upper()
            if u == "[LEAKAGE]":
                skip = True
                continue
            if skip and line.startswith("["): skip = False
            if "BACKFLOW ALLOWED" in u: continue
            if not skip: f.write(line)

def run_wntr_simulation(tmp_path):
    """Menjalankan simulasi menggunakan engine WNTR"""
    wn = wntr.network.WaterNetworkModel(tmp_path)
    sim = wntr.sim.EpanetSimulator(wn)
    results = sim.run_sim()
    return wn, results

def run_epyt_optimization(tmp_path, standar_pipa):
    """Logika Auto-Solver Diameter menggunakan engine EPyT"""
    d = epanet(tmp_path)
    link_ids = d.getLinkNameID()
    diameter_awal = d.getLinkDiameter()

    # Reset awal ke pipa besar agar tidak error (Trik Hacker)
    for i in range(len(link_ids)):
        d.setLinkDiameter(i + 1, 600)

    # Iterasi optimasi (5 kali)
    for _ in range(5):
        d.openHydraulicAnalysis()
        d.runHydraulicAnalysis()
        d.closeHydraulicAnalysis()
        velocity = d.getLinkVelocity()
        for i in range(len(link_ids)):
            v = abs(velocity[i])
            d_now = d.getLinkDiameter(i + 1)
            if 0.001 < v < 0.5:
                kandidat = [x for x in standar_pipa if x < d_now]
                if kandidat: d.setLinkDiameter(i + 1, max(kandidat))
            elif v > 2.0:
                kandidat = [x for x in standar_pipa if x > d_now]
                if kandidat: d.setLinkDiameter(i + 1, min(kandidat))
    
    return d, link_ids, diameter_awal
