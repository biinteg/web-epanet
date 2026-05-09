import streamlit as st
from epyt import epanet
import tempfile
import os
import pandas as pd

# Konfigurasi Halaman agar lebar
st.set_page_config(page_title="EPANET Auto-Solver", layout="wide")

st.title("Auto-Solver Jaringan Pipa (Engine: EPyT) 🚀")
st.write("Sistem akan menganalisis kecepatan air dan mencoba memperbaiki diameter pipa secara otomatis.")

uploaded_file = st.file_uploader("Upload File .inp EPANET", type=['inp'])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".inp") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        d = epanet(tmp_path)
        
        # --- PERBAIKAN MULAI PROSES SOLVER EPyT ---
        # Buka mesin hidrolika, jalankan di detik ke-0, lalu ambil datanya
        d.openHydraulicAnalysis()
        d.initializeHydraulicAnalysis(0)
        d.runHydraulicAnalysis()
        
        link_ids = d.getLinkNameID()
        diams = d.getLinkDiameter()
        vels = d.getLinkVelocity() # Mengambil kecepatan dari mesin yang sedang jalan
        
        d.closeHydraulicAnalysis() # Tutup mesin
        # ------------------------------------------
        
        # Aturan Pipa di Pasaran (dalam mm)
        standar_pipa = [40, 50, 75, 100, 150, 200, 250, 300, 400]
        
        isu_ditemukan = 0
        isu_diperbaiki = 0
        
        data_tabel = []

        # Analisis tiap pipa
        for i in range(len(link_ids)):
            v = abs(vels[i]) 
            D_awal = diams[i]
            status_v = "OK"
            D_baru = D_awal
            
            if v < 0.3 and v > 0.01: 
                isu_ditemukan += 1
                status_v = "Terlalu Lambat"
                kecil = [p for p in standar_pipa if p < D_awal]
                if kecil:
                    D_baru = max(kecil)
                    isu_diperbaiki += 1
                    
            elif v > 2.0: 
                isu_ditemukan += 1
                status_v = "Terlalu Cepat"
                besar = [p for p in standar_pipa if p > D_awal]
                if besar:
                    D_baru = min(besar)
                    isu_diperbaiki += 1

            if D_baru != D_awal:
                d.setLinkDiameter(i + 1, D_baru) # Index EPANET selalu mulai dari 1
            
            data_tabel.append({
                "ID Pipa": link_ids[i],
                "Diameter (mm)": D_baru,
                "Kecepatan (m/s)": round(v, 2),
                "Status Kecepatan": status_v
            })

        st.markdown("### Ringkasan")
        col1, col2, col3 = st.columns(3)
        col1.metric("Issues Ditemukan", isu_ditemukan)
        col2.metric("Issues Diperbaiki", isu_diperbaiki)
        col3.metric("Sisa Issues", isu_ditemukan - isu_diperbaiki)

        st.markdown("### Detail Hasil")
        df = pd.DataFrame(data_tabel)
        def warnai_status(val):
            color = 'green' if val == 'OK' else 'orange' if val == 'Terlalu Lambat' else 'red'
            return f'color: {color}'
        st.dataframe(df.style.map(warnai_status, subset=['Status Kecepatan']), use_container_width=True)

        st.markdown("### Unduh Hasil")
        new_inp_path = tmp_path.replace(".inp", "_optimized.inp")
        d.saveInputFile(new_inp_path)
        
        with open(new_inp_path, "rb") as file:
            st.download_button(
                label="Unduh File .INP Hasil Optimasi",
                data=file,
                file_name="Jaringan_Optimasi.inp",
                mime="text/plain"
            )

    except Exception as e:
        st.error(f"Gagal menjalankan solver: {e}")
        st.info("Pastikan jaringan awal tidak error (misal: pipa melawan gravitasi seperti sebelumnya).")
        
    finally:
        d.unload()
        os.remove(tmp_path)
        if 'new_inp_path' in locals() and os.path.exists(new_inp_path):
            os.remove(new_inp_path)
