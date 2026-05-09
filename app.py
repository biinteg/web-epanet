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
            st.write("Mendiagnosis kesehatan tekanan air dan mencari lokasi terbaik untuk **Pressure Reducing Valve (PRV)** secara otomatis.")
            
            # --- 🧹 AUTO-CLEANER ERROR 201 ---
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

            # --- ALGORITMA AUTO-PILOT PRV ---
            st.markdown("---")
            st.markdown("### 2. 🤖 Auto-Pilot PRV (Pencari Pipa Terbaik)")
            st.write("Sistem akan mencoba memasang PRV di SETIAP pipa satu per satu di latar belakang, lalu memilihkan lokasi PRV yang paling banyak menyelamatkan Node.")
            
            setting_prv_auto = st.number_input("Setting Target Tekanan PRV (m):", min_value=10.0, max_value=100.0, value=50.0)

            if st.button("Jalankan Triple-Pilot PRV (God Mode) 🚀"):
                with st.spinner('Mencari konfigurasi 3 katup terbaik... Mohon bersabar!'):
                    best_pipes = None
                    best_aman_count = -1
                    best_tekanan = None
                    best_wn = None
                    
                    all_pipes = wn.pipe_name_list
                    # Pipa target utama yang dicurigai (agar looping lebih cepat)
                    # p1, p3, p7, p13, p2 biasanya adalah kunci
                    
                    for i in range(len(all_pipes)):
                        for j in range(i + 1, len(all_pipes)):
                            for k in range(j + 1, len(all_pipes)):
                                p1_n, p2_n, p3_n = all_pipes[i], all_pipes[j], all_pipes[k]
                                
                                try:
                                    wn_test = wntr.network.WaterNetworkModel(tmp_path)
                                    
                                    # Pasang 3 PRV sekaligus
                                    for p_target in [p1_n, p2_n, p3_n]:
                                        p_obj = wn_test.get_link(p_target)
                                        wn_test.remove_link(p_target)
                                        wn_test.add_valve(f"PRV_{p_target}", p_obj.start_node_name, p_obj.end_node_name, 
                                                        diameter=p_obj.diameter, valve_type='PRV', initial_setting=setting_prv_auto)
                                    
                                    sim_test = wntr.sim.EpanetSimulator(wn_test)
                                    res_test = sim_test.run_sim()
                                    tekanan_test = res_test.node['pressure'].loc[0]
                                    
                                    aman_count = sum(1 for n in wn_test.junction_name_list if 15 <= tekanan_test[n] <= 80)
                                        
                                    if aman_count > best_aman_count:
                                        best_aman_count = aman_count
                                        best_pipes = (p1_n, p2_n, p3_n)
                                        best_tekanan = tekanan_test
                                        best_wn = wn_test
                                        
                                    if aman_count >= len(wn_test.junction_name_list): break
                                except: continue
                            if best_aman_count >= len(wn.junction_name_list): break
                        if best_aman_count >= len(wn.junction_name_list): break

                    if best_pipes:
                        st.success(f"✨ KONFIGURASI SEMPURNA! Pasang PRV di: **{best_pipes[0]}, {best_pipes[1]}, dan {best_pipes[2]}**")
                        # ... sisa kode tabel perbandingan ...
                    
                   # --- TAMPILKAN HASIL TERBAIK (VERSI DOUBLE-PILOT) ---
                    if best_pipes:
                        st.success(f"✨ SOLUSI DITEMUKAN! Pasang dua PRV di Pipa: **{best_pipes[0]}** dan **{best_pipes[1]}**")
                        st.info(f"Kombinasi ini berhasil membuat **{best_aman_count} Node** menjadi AMAN (Hijau).")
                        
                        # Tabel Hasil Perbandingan
                        data_banding = []
                        for node_name in wn.junction_name_list:
                            p_lama = tekanan_t0[node_name]
                            p_baru = best_tekanan[node_name]
                            status_baru = "Aman" if 15 <= p_baru <= 80 else ("Terlalu Rendah" if p_baru < 15 else "Bahaya (Terlalu Tinggi)")
                            
                            data_banding.append({
                                "ID Node": node_name,
                                "Tekanan Lama (m)": round(p_lama, 2),
                                "Tekanan Baru (m)": round(p_baru, 2),
                                "Status Baru": status_baru
                            })
                        
                        df_banding = pd.DataFrame(data_banding)
                        def warnai_status(val):
                            if val == 'Aman': return 'color: green'
                            elif val == 'Terlalu Rendah': return 'color: orange'
                            else: return 'color: red'
                            
                        st.dataframe(df_banding.style.map(warnai_status, subset=['Status Baru']), use_container_width=True)

                        # Unduh File Hasil Operasi Dua PRV
                        st.markdown("#### Unduh Jaringan Sempurna")
                        new_inp_prv = tmp_path.replace(".inp", "_DoublePRV.inp")
                        wntr.network.write_inpfile(best_wn, new_inp_prv)
                        with open(new_inp_prv, "rb") as file:
                            st.download_button(label="Unduh File .INP (Sudah Ada 2 PRV)", data=file, file_name=f"Jaringan_Dua_PRV.inp", mime="text/plain")
                    else:
                        st.error("Gagal menemukan kombinasi PRV yang cocok.")

    except Exception as e:
        st.error(f"Gagal menjalankan analisis: {e}")
        st.info("Pastikan file .inp Anda valid.")
        
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)
        if 'new_inp_path' in locals() and os.path.exists(new_inp_path): os.remove(new_inp_path)
        if 'new_inp_prv' in locals() and os.path.exists(new_inp_prv): os.remove(new_inp_prv)
