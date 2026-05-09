import streamlit as st
from epyt import epanet
import tempfile
import os
import pandas as pd

# Konfigurasi Halaman agar lebar seperti di gambar
st.set_page_config(page_title="EPANET Auto-Solver", layout="wide")

st.title("Auto-Solver Jaringan Pipa (Engine: EPyT) 🚀")
st.write("Sistem akan menganalisis kecepatan air dan mencoba memperbaiki diameter pipa secara otomatis.")

uploaded_file = st.file_uploader("Upload File .inp EPANET", type=['inp'])

if uploaded_file is not None:
    # 1. Simpan file sementara
    with tempfile.NamedTemporaryFile(delete=False, suffix=".inp") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        # 2. Muat ke EPyT
        d = epanet(tmp_path)
        
        # --- MULAI PROSES SOLVER ---
        d.solve() # Jalankan simulasi awal
        
        # Ambil data jaringan
        link_ids = d.getLinkNameID()
        diams = d.getLinkDiameter()
        vels = d.getLinkVelocity() # Kecepatan saat ini
        
        # Aturan Pipa di Pasaran (dalam mm)
        standar_pipa = [40, 50, 75, 100, 150, 200, 250, 300, 400]
        
        isu_ditemukan = 0
        isu_diperbaiki = 0
        
        data_tabel = []

        # 3. Analisis tiap pipa
        for i in range(len(link_ids)):
            v = abs(vels[i]) # Kecepatan absolut
            D_awal = diams[i]
            status_v = "OK"
            D_baru = D_awal
            
            if v < 0.3 and v > 0.01: # Terlalu lambat (kecuali pipa mati)
                isu_ditemukan += 1
                status_v = "Terlalu Lambat"
                # Cari pipa 1 tingkat lebih kecil
                kecil = [p for p in standar_pipa if p < D_awal]
                if kecil:
                    D_baru = max(kecil)
                    isu_diperbaiki += 1
                    
            elif v > 2.0: # Terlalu kencang
                isu_ditemukan += 1
                status_v = "Terlalu Cepat"
                # Cari pipa 1 tingkat lebih besar
                besar = [p for p in standar_pipa if p > D_awal]
                if besar:
                    D_baru = min(besar)
                    isu_diperbaiki += 1

            # Terapkan perubahan diameter ke EPyT jika ada perubahan
            if D_baru != D_awal:
                d.setLinkDiameter(i + 1, D_baru) # Index EPyT mulai dari 1
            
            # Masukkan ke tabel
            data_tabel.append({
                "ID Pipa": link_ids[i],
                "Diameter (mm)": D_baru,
                "Kecepatan (m/s)": round(v, 2),
                "Status Kecepatan": status_v
            })

        # 4. Buat Tampilan Ringkasan (Seperti di Gambar)
        st.markdown("### Ringkasan")
        col1, col2, col3 = st.columns(3)
        col1.metric("Issues Ditemukan", isu_ditemukan)
        col2.metric("Issues Diperbaiki", isu_diperbaiki)
        col3.metric("Sisa Issues", isu_ditemukan - isu_diperbaiki)

        # 5. Tampilkan Tabel Detail
        st.markdown("### Detail Hasil")
        df = pd.DataFrame(data_tabel)
        # Menambahkan warna pada tabel
        def warnai_status(val):
            color = 'green' if val == 'OK' else 'orange' if val == 'Terlalu Lambat' else 'red'
            return f'color: {color}'
        st.dataframe(df.style.map(warnai_status, subset=['Status Kecepatan']), use_container_width=True)

        # 6. Tombol Unduh File .INP yang sudah diperbaiki
        st.markdown("### Unduh Hasil")
        # Simpan file baru
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
