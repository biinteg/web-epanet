import streamlit as st
from epyt import epanet
import tempfile
import os
import pandas as pd

# Konfigurasi Halaman
st.set_page_config(page_title="EPANET Pro Toolkit", layout="wide")

# --- MEMBUAT SIDEBAR UNTUK MENU NAVIGASI ---
st.sidebar.title("EPANET Pro Toolkit 🛠️")
st.sidebar.write("Pilih mode analisis:")
# Membuat tombol radio (pilihan) di menu samping
menu = st.sidebar.radio(
    "Navigasi Fitur:", 
    ["🚀 Auto-Solver (Diameter Pipa)", "🩺 Analisis Tekanan (Pressure Node)"]
)

st.sidebar.markdown("---")
st.sidebar.info("Aplikasi ini dibuat dengan EPyT & Streamlit.")

# --- BAGIAN UTAMA WEBSITE ---
st.title(menu) # Judul halaman akan berubah sesuai menu yang dipilih

uploaded_file = st.file_uploader("Upload File .inp EPANET Anda di sini", type=['inp'])

if uploaded_file is not None:
    # 1. Simpan file sementara
    with tempfile.NamedTemporaryFile(delete=False, suffix=".inp") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        # ==========================================
        # FITUR 1: AUTO-SOLVER DIAMETER PIPA
        # ==========================================
        if menu == "🚀 Auto-Solver (Diameter Pipa)":
            st.write("Sistem akan menggunakan *Trik Pipa Raksasa* untuk mencegah Error, lalu mengoptimasi diameternya secara otomatis.")
            
            d = epanet(tmp_path)
            link_ids = d.getLinkNameID()
            diams_asli = d.getLinkDiameter() 
            
            # Trik Hacker: Paksa ubah ke 600mm
            for i in range(len(link_ids)):
                d.setLinkDiameter(i + 1, 600) 
                
            d.openHydraulicAnalysis()
            d.initializeHydraulicAnalysis(0)
            d.runHydraulicAnalysis()
            vels = d.getLinkVelocity() 
            d.closeHydraulicAnalysis() 
            
            standar_pipa = [50, 75, 100, 150, 200, 250, 300, 400, 500, 600, 800]
            isu_diperbaiki = 0
            data_tabel = []

            for i in range(len(link_ids)):
                v = abs(vels[i]) 
                D_asli = diams_asli[i]   
                D_komputasi = 600
                status_v = "OK"
                D_baru = D_komputasi
                
                if v < 0.5 and v > 0.001: 
                    status_v = "Diperkecil"
                    kecil = [p for p in standar_pipa if p < D_komputasi]
                    if kecil:
                        D_baru = max(kecil) 
                elif v > 2.0: 
                    status_v = "Diperbesar"
                    besar = [p for p in standar_pipa if p > D_komputasi]
                    if besar:
                        D_baru = min(besar)

                if D_baru != D_asli:
                    isu_diperbaiki += 1

                d.setLinkDiameter(i + 1, D_baru) 
                
                data_tabel.append({
                    "ID Pipa": link_ids[i],
                    "Diameter Asli (mm)": D_asli,
                    "Diameter Optimasi (mm)": D_baru,
                    "Kecepatan (m/s)": round(v, 2),
                    "Status": status_v
                })

            st.markdown("### Ringkasan Optimasi Diameter")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Pipa Jaringan", len(link_ids))
            col2.metric("Pipa Disesuaikan Sistem", isu_diperbaiki)
            col3.metric("Status Mesin", "Trik Raksasa Berhasil ✅")

            df = pd.DataFrame(data_tabel)
            st.dataframe(df, use_container_width=True)

            st.markdown("### Unduh Hasil Optimasi")
            new_inp_path = tmp_path.replace(".inp", "_optimized.inp")
            d.saveInputFile(new_inp_path) 
            with open(new_inp_path, "rb") as file:
                st.download_button(label="Unduh File .INP (Sudah Diperbaiki)", data=file, file_name="Jaringan_Optimasi_Diameter.inp", mime="text/plain")
            
            d.unload() # Tutup mesin

        # ==========================================
        # FITUR 2: ANALISIS TEKANAN (PRESSURE)
        # ==========================================
        elif menu == "🩺 Analisis Tekanan (Pressure Node)":
            st.write("Mendiagnosis kesehatan tekanan air di setiap persimpangan (Node) untuk mencari potensi kebocoran atau ledakan pipa.")
            
            d = epanet(tmp_path)
            d.openHydraulicAnalysis()
            d.initializeHydraulicAnalysis(0)
            d.runHydraulicAnalysis()
            
            node_ids = d.getNodeNameID()
            elevations = d.getNodeElevations()
            pressures = d.getNodePressure()
            d.closeHydraulicAnalysis() 
            
            data_tabel = []
            node_rendah = 0
            node_aman = 0
            node_tinggi = 0

            for i in range(len(node_ids)):
                p = pressures[i]
                elev = elevations[i]
                
                # Abaikan Reservoir/Tangki
                if "Res" in node_ids[i] or elev == 0:
                    continue
                    
                status_p = "Aman"
                if p < 15:
                    status_p = "Terlalu Rendah"
                    node_rendah += 1
                elif p > 80:
                    status_p = "Bahaya (Terlalu Tinggi)"
                    node_tinggi += 1
                else:
                    node_aman += 1

                data_tabel.append({
                    "ID Node": node_ids[i],
                    "Elevasi Tanah (m)": round(elev, 2),
                    "Tekanan / Pressure (m)": round(p, 2),
                    "Status": status_p
                })

            st.markdown("### Ringkasan Kesehatan Node")
            col1, col2, col3 = st.columns(3)
            col1.metric("Node Tekanan Rendah (< 15m)", node_rendah)
            col2.metric("Node Aman (15m - 80m)", node_aman)
            col3.metric("Node Bahaya Meledak (> 80m)", node_tinggi)

            df = pd.DataFrame(data_tabel)
            def warnai_status(val):
                if val == 'Aman': color = 'green'
                elif val == 'Terlalu Rendah': color = 'orange'
                else: color = 'red'
                return f'color: {color}'
                
            st.dataframe(df.style.map(warnai_status, subset=['Status']), use_container_width=True)
            d.unload() # Tutup mesin

    except Exception as e:
        st.error(f"Gagal menjalankan analisis: {e}")
        st.info("Pastikan jaringan tidak memiliki error fundamental (seperti Reservoir terlalu rendah).")
        
    finally:
        # Bersihkan memori dan hapus file sementara
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        if 'new_inp_path' in locals() and os.path.exists(new_inp_path):
            os.remove(new_inp_path)
