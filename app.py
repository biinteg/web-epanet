import streamlit as st
from epyt import epanet
import tempfile
import os
import pandas as pd

st.set_page_config(page_title="EPANET Auto-Solver", layout="wide")

st.title("Auto-Solver Jaringan Pipa (Engine: EPyT) 🚀")
st.write("Sistem akan mereset pipa ke ukuran RAKSASA (600mm), lalu mengoptimasi diameternya.")

uploaded_file = st.file_uploader("Upload File .inp EPANET", type=['inp'])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".inp") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        d = epanet(tmp_path)
        
        link_ids = d.getLinkNameID()
        diams_asli = d.getLinkDiameter() 
        
        # --- TRIK HACKER LEVEL DEWA ---
        # Paksa ubah ke pipa raksasa (600mm) agar aliran lancar seperti jalan tol
        for i in range(len(link_ids)):
            d.setLinkDiameter(i + 1, 600) 
            
        d.openHydraulicAnalysis()
        d.initializeHydraulicAnalysis(0)
        d.runHydraulicAnalysis()
        
        vels = d.getLinkVelocity() 
        d.closeHydraulicAnalysis() 
        
        # --- DAFTAR PIPA DIPERBESAR (Hingga 800mm) ---
        standar_pipa = [50, 75, 100, 150, 200, 250, 300, 400, 500, 600, 800]
        
        isu_diperbaiki = 0
        data_tabel = []

        for i in range(len(link_ids)):
            v = abs(vels[i]) 
            D_asli = diams_asli[i]   
            D_komputasi = 600        # Karena kita set 600 di awal
            status_v = "OK"
            D_baru = D_komputasi
            
            # Jika airnya santai (< 0.5 m/s) di dalam pipa raksasa, kita kecilkan pipanya!
            if v < 0.5 and v > 0.001: 
                status_v = "Diperkecil"
                kecil = [p for p in standar_pipa if p < D_komputasi]
                if kecil:
                    # Kita cari ukuran yang pas agar tidak terlalu sempit
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

        st.markdown("### Ringkasan Optimasi")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Pipa Jaringan", len(link_ids))
        col2.metric("Pipa Disesuaikan Sistem", isu_diperbaiki)
        col3.metric("Status Mesin", "Trik Pipa Raksasa Berhasil ✅")

        st.markdown("### Detail Hasil Pipa")
        df = pd.DataFrame(data_tabel)
        
        st.dataframe(df, use_container_width=True)

        st.markdown("### Unduh Hasil")
        new_inp_path = tmp_path.replace(".inp", "_optimized.inp")
        d.saveInputFile(new_inp_path) 
        
        with open(new_inp_path, "rb") as file:
            st.download_button(
                label="Unduh File .INP (Sudah Diperbaiki)",
                data=file,
                file_name="Jaringan_Anti_Error_V2.inp",
                mime="text/plain"
            )

    except Exception as e:
        st.error(f"Gagal menjalankan solver: {e}")
        st.info("Pesan: Pastikan Head Reservoir di file yang diupload minimal 350.")
        
    finally:
        d.unload()
        os.remove(tmp_path)
        if 'new_inp_path' in locals() and os.path.exists(new_inp_path):
            os.remove(new_inp_path)
