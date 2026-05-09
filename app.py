import streamlit as st
import tempfile
import os
import pandas as pd
from epyt import epanet  # Tambahkan ini untuk engine EPyT

# IMPORT DARI FILE BUATAN SENDIRI
from utils import warnai_status_tekanan, warnai_status_solver, tampilkan_network
from solver import clean_inp_file, run_wntr_simulation, run_epyt_optimization

# 1. Konfigurasi Halaman
st.set_page_config(page_title="EPANET Pro Toolkit", layout="wide")

# 2. Sidebar & Menu
st.sidebar.title("EPANET Pro Toolkit 🛠️")
menu = st.sidebar.radio(
    "Navigasi:",
    ["🚀 Auto-Solver (Engine: EPyT)", "🩺 Analisis Tekanan & Auto-PRV (Engine: WNTR)"]
)

st.sidebar.markdown("---")
st.sidebar.info("Multi-engine: EPyT + WNTR")

# 3. Judul Utama
st.title(menu)

# 4. DEFINISI VARIABEL (Agar tidak NameError)
uploaded_file = st.file_uploader("Upload file .inp EPANET", type=["inp"])

# 5. LOGIKA UTAMA
if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".inp") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        if menu == "🚀 Auto-Solver (Engine: EPyT)":
            st.write("🔧 Optimasi diameter otomatis berdasarkan kecepatan (0.5–2.0 m/s)")
            
            standar = [50, 75, 100, 150, 200, 250, 300, 400, 500, 600, 800]
            
            # Panggil fungsi dari solver.py
            d, link_ids, diam_awal = run_epyt_optimization(tmp_path, standar)
            
            # Ambil data final
            velocity_final = d.getLinkVelocity()
            hasil = []
            for i in range(len(link_ids)):
                akhir = d.getLinkDiameter(i + 1)
                status = "Diperbesar" if akhir > diam_awal[i] else ("Diperkecil" if akhir < diam_awal[i] else "Tetap")
                hasil.append({
                    "ID Pipa": link_ids[i], 
                    "Diameter Awal": f"{diam_awal[i]:.0f} mm",
                    "Diameter Baru": f"{akhir:.0f} mm", 
                    "Velocity": f"{abs(velocity_final[i]):.2f} m/s", 
                    "Status": status
                })
            
            st.dataframe(pd.DataFrame(hasil).style.map(warnai_status_solver, subset=["Status"]), use_container_width=True)
            
            # Simpan dan download
            new_inp = tmp_path.replace(".inp", "_optimized.inp")
            d.saveInputFile(new_inp)
            with open(new_inp, "rb") as f:
                st.download_button("💾 Unduh File Optimasi", data=f, file_name="Optimasi_Diameter.inp")
            
            d.unload()

        elif menu == "🩺 Analisis Tekanan & Auto-PRV (Engine: WNTR)":
            # Bersihkan file dari tag leakage
            clean_inp_file(tmp_path)
            
            # Jalankan WNTR
            wn, results = run_wntr_simulation(tmp_path)
            tekanan_awal = results.node["pressure"].iloc[0]
            
            # Visualisasi dari utils.py
            tampilkan_network(wn, tekanan_awal, "Kondisi Tekanan Jaringan")
            
            # Tampilkan tabel tekanan
            data_p = []
            for node in wn.junction_name_list:
                p = tekanan_awal[node]
                p = 0 if pd.isna(p) or p < -100 else p
                status = "Aman" if 15 <= p <= 80 else "Bahaya"
                data_p.append({"Node": node, "Tekanan": round(p, 2), "Status": status})
            
            st.dataframe(pd.DataFrame(data_p).style.map(warnai_status_tekanan, subset=["Status"]), use_container_width=True)

    except Exception as e:
        st.error(f"Terjadi Kesalahan: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
