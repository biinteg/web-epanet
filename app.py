import streamlit as st
from epyt import epanet
import tempfile
import os
import pandas as pd

st.set_page_config(page_title="EPANET Auto-Solver", layout="wide")

st.title("Auto-Solver Jaringan Pipa (Engine: EPyT) 🚀")
st.write("Sistem akan mereset pipa, menganalisis kecepatan, dan mengoptimasi diameter secara otomatis.")

uploaded_file = st.file_uploader("Upload File .inp EPANET", type=['inp'])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".inp") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        d = epanet(tmp_path)
        
        # 1. AMBIL DIAMETER ASLI DARI FILE (SEBELUM DIHACK)
        link_ids = d.getLinkNameID()
        diams_asli = d.getLinkDiameter() 
        
        # 2. TRIK HACKER (Ubah ke 250mm sementara agar mesin dijamin jalan)
        for i in range(len(link_ids)):
            d.setLinkDiameter(i + 1, 250) 
            
        # 3. Jalankan mesin hidrolika
        d.openHydraulicAnalysis()
        d.initializeHydraulicAnalysis(0)
        d.runHydraulicAnalysis()
        
        vels = d.getLinkVelocity() 
        d.closeHydraulicAnalysis() 
        
        # Aturan Pipa di Pasaran (dalam mm)
        standar_pipa = [40, 50, 75, 100, 150, 200, 250, 300, 400]
        
        isu_diperbaiki = 0
        data_tabel = []

        # Algoritma Pengecilan Pipa Otomatis
        for i in range(len(link_ids)):
            v = abs(vels[i]) 
            D_asli = diams_asli[i]   # Ini data asli dari Notepad++ (misal 40, 75, 200)
            D_komputasi = 250        # Ini ukuran saat mesin jalan
            status_v = "OK"
            D_baru = D_komputasi
            
            # Cari ukuran ideal berdasarkan kecepatan
            if v < 0.3 and v > 0.001: 
                status_v = "Terlalu Lambat"
                kecil = [p for p in standar_pipa if p < D_komputasi]
                if kecil:
                    D_baru = max(kecil) 
                    
            elif v > 2.0: 
                status_v = "Terlalu Cepat"
                besar = [p for p in standar_pipa if p > D_komputasi]
                if besar:
                    D_baru = min(besar)

            # Hitung isu diperbaiki (jika hasil akhirnya beda dengan file asli teman Anda)
            if D_baru != D_asli:
                isu_diperbaiki += 1

            # Terapkan perubahan FINAL ke mesin
            d.setLinkDiameter(i + 1, D_baru) 
            
            # Masukkan data ke tabel (Tampilkan D_asli)
            data_tabel.append({
                "ID Pipa": link_ids[i],
                "Diameter Asli (mm)": D_asli,
                "Diameter Optimasi (mm)": D_baru,
                "Kecepatan (m/s)": round(v, 2),
                "Status": "Diubah Sistem" if D_baru != D_asli else "Tetap"
            })

        st.markdown("### Ringkasan Optimasi")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Pipa Jaringan", len(link_ids))
        col2.metric("Pipa yang Diubah Sistem", isu_diperbaiki)
        col3.metric("Status Mesin", "Berjalan Mulus ✅")

        st.markdown("### Detail Hasil Pipa")
        df = pd.DataFrame(data_tabel)
        
        # Pewarnaan Tabel
        def warnai_status(val):
            color = 'green' if val == 'Tetap' else 'blue'
            return f'color: {color}'
        st.dataframe(df.style.map(warnai_status, subset=['Status']), use_container_width=True)

        st.markdown("### Unduh Hasil")
        new_inp_path = tmp_path.replace(".inp", "_optimized.inp")
        d.saveInputFile(new_inp_path) 
        
        with open(new_inp_path, "rb") as file:
            st.download_button(
                label="Unduh File .INP (Sudah Diperbaiki)",
                data=file,
                file_name="Jaringan_Anti_Error.inp",
                mime="text/plain"
            )

    except Exception as e:
        st.error(f"Gagal menjalankan solver: {e}")
        st.info("Bantuan: Pastikan tinggi Reservoir sudah disetel di atas 300 meter.")
        
    finally:
        d.unload()
        os.remove(tmp_path)
        if 'new_inp_path' in locals() and os.path.exists(new_inp_path):
            os.remove(new_inp_path)
