# app.py (Lanjutan dari screenshot Anda)
import streamlit as st
import tempfile
import os
import pandas as pd
from solver import clean_inp_file, run_wntr_simulation, run_epyt_optimization
from utils import warnai_status_tekanan, warnai_status_solver, tampilkan_network

# ... (kode awal s/d st.file_uploader)

if uploaded_file is not None:
    # (kode penyimpanan tmp_path)
    
    try:
        if menu == "🚀 Auto-Solver (Engine: EPyT)":
            standar = [50, 75, 100, 150, 200, 250, 300, 400, 500, 600, 800]
            d, link_ids, diam_awal = run_epyt_optimization(tmp_path, standar)
            
            # Olah data untuk tabel
            velocity_final = d.getLinkVelocity()
            hasil = []
            for i in range(len(link_ids)):
                akhir = d.getLinkDiameter(i + 1)
                status = "Diperbesar" if akhir > diam_awal[i] else ("Diperkecil" if akhir < diam_awal[i] else "Tetap")
                hasil.append({
                    "ID Pipa": link_ids[i], "Diameter Awal": diam_awal[i],
                    "Diameter Baru": akhir, "Velocity": round(abs(velocity_final[i]), 2), "Status": status
                })
            
            st.dataframe(pd.DataFrame(hasil).style.map(warnai_status_solver, subset=["Status"]))
            d.unload()

        elif menu == "🩺 Analisis Tekanan & Auto-PRV (Engine: WNTR)":
            clean_inp_file(tmp_path)
            wn, results = run_wntr_simulation(tmp_path)
            tekanan_awal = results.node["pressure"].iloc[0]
            
            tampilkan_network(wn, tekanan_awal, "Kondisi Tekanan Jaringan")
            
            # Logika Triple PRV (Bisa Anda masukkan di sini)
            st.info("Gunakan tombol 'Cari Kombinasi' untuk optimasi tekanan.")

    except Exception as e:
        st.error(f"Terjadi Kesalahan: {e}")
