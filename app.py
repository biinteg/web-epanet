import streamlit as st
from epyt import epanet
import wntr
import tempfile
import os
import pandas as pd

# Konfigurasi Halaman
st.set_page_config(page_title="EPANET Pro Toolkit", layout="wide")

st.sidebar.title("EPANET Pro Toolkit 🛠️")
st.sidebar.write("Pilih mode analisis:")
menu = st.sidebar.radio(
    "Navigasi Fitur:", 
    ["🚀 Auto-Solver (Engine: EPyT)", "🩺 Analisis Tekanan & Auto-PRV (Engine: WNTR)"]
)

st.sidebar.markdown("---")
st.sidebar.info("Aplikasi ini ditenagai oleh multi-engine: EPyT dan WNTR.")

st.title(menu) 

uploaded_file = st.file_uploader("Upload File .inp EPANET Anda di sini", type=['inp'])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".inp") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        # ==========================================
        # FITUR 1: AUTO-SOLVER (MESIN: EPyT)
        # ==========================================
        if menu == "🚀 Auto-Solver (Engine: EPyT)":
            st.write("Sistem akan menggunakan *Trik Pipa Raksasa* untuk mencegah Error, lalu mengoptimasi diameternya secara otomatis.")
            
            d = epanet(tmp_path)
            link_ids = d.getLinkNameID()
            diams_asli = d.getLinkDiameter() 
            
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
                    if kecil: D_baru = max(kecil) 
                elif v > 2.0: 
                    status_v = "Diperbesar"
                    besar = [p for p in standar_pipa if p > D_komputasi]
                    if besar: D_baru = min(besar)

                if D_baru != D_asli: isu_diperbaiki += 1
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
            col1.metric("Total Pipa", len(link_ids))
            col2.metric("Dioptimasi", isu_diperbaiki)
            col3.metric("Engine", "EPyT Berhasil ✅")

            df = pd.DataFrame(data_tabel)
            st.dataframe(df, use_container_width=True)

            st.markdown("### Unduh Hasil Optimasi")
            new_inp_path = tmp_path.replace(".inp", "_optimized.inp")
            d.saveInputFile(new_inp_path) 
            with open(new_inp_path, "rb") as file:
                st.download_button(label="Unduh File .INP (Sudah Diperbaiki)", data=file, file_name="Jaringan_Optimasi_Diameter.inp", mime="text/plain")
            d.unload() 

        # ==========================================
        # FITUR 2: ANALISIS TEKANAN & AUTO-PRV (MESIN: WNTR)
        # ==========================================
        elif menu == "🩺 Analisis Tekanan & Auto-PRV (Engine: WNTR)":
            st.write("Mendiagnosis kesehatan tekanan air dan menyediakan fitur pemasangan **Pressure Reducing Valve (PRV)** secara otomatis.")
            
            # Auto-Cleaner untuk menembus WNTR
            with open(tmp_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            with open(tmp_path, 'w', encoding='utf-8') as f:
                skip_mode = False
                for line in lines:
                    line_upper = line.strip().upper()
                    if line_upper == '[LEAKAGE]':
                        skip_mode = True
                        continue
                    if skip_mode and line.startswith('['):
                        skip_mode = False 
                    if "BACKFLOW ALLOWED" in line_upper:
                        continue 
                    if not skip_mode:
                        f.write(line)

            wn = wntr.network.WaterNetworkModel(tmp_path)
            sim = wntr.sim.EpanetSimulator(wn)
            results = sim.run_sim()
            tekanan_t0 = results.node['pressure'].loc[0]
            
            data_tabel = []
            for node_name in wn.junction_name_list:
                p = tekanan_t0[node_name]
                status_p = "Aman"
                if p < 15: status_p = "Terlalu Rendah"
                elif p > 80: status_p = "Bahaya (Terlalu Tinggi)"

                data_tabel.append({
                    "ID Node": node_name,
                    "Tekanan Awal (m)": round(p, 2),
                    "Status": status_p
                })

            st.markdown("### 1. Diagnosis Tekanan Awal")
            df = pd.DataFrame(data_tabel)
            def warnai_status(val):
                if val == 'Aman': color = 'green'
                elif val == 'Terlalu Rendah': color = 'orange'
                else: color = 'red'
                return f'color: {color}'
            st.dataframe(df.style.map(warnai_status, subset=['Status']), use_container_width=True)

            st.markdown("---")
            st.markdown("### 2. 🛠️ Fix Pressure Otomatis (Auto-PRV)")
            st.write("Potong pipa lama, ganti dengan PRV untuk menurunkan tekanan yang rawan meledak.")
            
            pipe_list = wn.pipe_name_list
            default_idx = pipe_list.index('p7') if 'p7' in pipe_list else 0

            col1, col2 = st.columns(2)
            pipa_target = col1.selectbox("Pilih Pipa yang akan diganti PRV:", pipe_list, index=default_idx)
            setting_prv = col2.number_input("Setting Target Tekanan (m):", min_value=10.0, max_value=100.0, value=50.0)

            if st.button("Pasang PRV & Simulasi Ulang 🚀"):
                # Operasi Bedah Jaringan
                pipa_obj = wn.get_link(pipa_target)
                n1 = pipa_obj.start_node_name
                n2 = pipa_obj.end_node_name
                d_pipa = pipa_obj.diameter

                # Buang pipa lama, masukkan Valve PRV
                wn.remove_link(pipa_target)
                nama_prv = f"PRV_{pipa_target}"
                wn.add_valve(nama_prv, n1, n2, diameter=d_pipa, valve_type='PRV', minor_loss=0.0, initial_setting=setting_prv)

                st.success(f"✅ Operasi Berhasil! Pipa '{pipa_target}' telah diganti dengan {nama_prv} (Setting: {setting_prv} m).")

                # Simulasi Ulang dengan Jaringan Baru
                sim_baru = wntr.sim.EpanetSimulator(wn)
                res_baru = sim_baru.run_sim()
                tekanan_baru = res_baru.node['pressure'].loc[0]

                # Bikin tabel perbandingan
                data_banding = []
                for node_name in wn.junction_name_list:
                    p_lama = tekanan_t0[node_name]
                    p_baru = tekanan_baru[node_name]
                    status_baru = "Aman" if 15 <= p_baru <= 80 else ("Terlalu Rendah" if p_baru < 15 else "Bahaya (Terlalu Tinggi)")
                    
                    data_banding.append({
                        "ID Node": node_name,
                        "Tekanan Lama (m)": round(p_lama, 2),
                        "Tekanan Baru (m)": round(p_baru, 2),
                        "Status Baru": status_baru
                    })
                
                st.markdown("#### Hasil Setelah Pemasangan PRV:")
                df_banding = pd.DataFrame(data_banding)
                st.dataframe(df_banding.style.map(warnai_status, subset=['Status Baru']), use_container_width=True)

                # Fitur Download Jaringan yang sudah disisipkan PRV
                st.markdown("#### Unduh Jaringan Baru")
                new_inp_prv = tmp_path.replace(".inp", "_with_PRV.inp")
                wntr.network.write_inpfile(wn, new_inp_prv)
                with open(new_inp_prv, "rb") as file:
                    st.download_button(label="Unduh File .INP (Sudah Ada PRV)", data=file, file_name=f"Jaringan_PRV_{pipa_target}.inp", mime="text/plain")

    except Exception as e:
        st.error(f"Gagal menjalankan analisis: {e}")
        st.info("Pastikan file .inp Anda valid dan tidak mengalami error fatal gravitasi.")
        
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)
        if 'new_inp_path' in locals() and os.path.exists(new_inp_path): os.remove(new_inp_path)
        if 'new_inp_prv' in locals() and os.path.exists(new_inp_prv): os.remove(new_inp_prv)
