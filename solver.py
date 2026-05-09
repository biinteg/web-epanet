# solver.py
import wntr
import os

def clean_inp_file(path):
    """Menghapus tag yang bikin WNTR crash"""
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
    wn = wntr.network.WaterNetworkModel(tmp_path)
    sim = wntr.sim.EpanetSimulator(wn)
    results = sim.run_sim()
    return wn, results
