import streamlit as st
from epyt import epanet
import wntr
import tempfile
import os
import pandas as pd
import matplotlib.pyplot as plt
from itertools import combinations
import numpy as np

# =====================================================
# FUNGSI WARNA
# =====================================================

def warnai_status_tekanan(val):
    if val == "Aman":
        return "color: limegreen; font-weight: bold;"
    else:
        return "color: red; font-weight: bold;"

def warnai_status_solver(val):
    if val == "Diperbesar":
        return "color: limegreen; font-weight: bold;"
    elif val == "Diperkecil":
        return "color: orange; font-weight: bold;"
    else:
        return "color: cyan; font-weight: bold;"

def tampilkan_network(wn, tekanan_dict=None, judul="Visualisasi Jaringan"):
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Plot network dasar
    wntr.graphics.plot_network(wn, title=judul, ax=ax)
    
    # Tambahkan scatter plot untuk node dengan warna berdasarkan tekanan
    if tekanan_dict is not None:
        node_xy = []
        node_colors = []
        node_labels = []
        
        for node_name in wn.junction_name_list:
            node = wn.get_node(node_name)
            x, y = node.coordinates
            node_xy.append([x, y])
            
            p = tekanan_dict[node_name]
            # Pengaman angka absurd
            if p < -100:
                p = 0
            
            if p < 15:
                node_colors.append("red")
            elif p > 80:
                node_colors.append("orange")
            else:
                node_colors.append("limegreen")
            
            node_labels.append(f"{node_name}\n{p:.1f}m")
        
        if node_xy:
            node_xy = np.array(node_xy)
            scatter = ax.scatter(node_xy[:, 0], node_xy[:, 1], 
                                c=node_colors, s=120, zorder=5, 
                                edgecolors='black', linewidth=1.5)
    
    # Legend
    if tekanan_dict is not None:
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor='limegreen',
                   markersize=12, label='Aman (15-80 m)', markeredgecolor='black'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='orange',
                   markersize=12, label='Tinggi (>80 m)', markeredgecolor='black'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='red',
                   markersize=12, label='Rendah (<15 m)', markeredgecolor='black')
        ]
        ax.legend(handles=legend_elements, loc='upper right', frameon=True)
    
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="EPANET Pro Toolkit",
    layout="wide"
)

st.sidebar.title("EPANET Pro Toolkit 🛠️")
st.sidebar.write("Pilih mode analisis:")

menu = st.sidebar.radio(
    "Navigasi:",
    [
        "🚀 Auto-Solver (Engine: EPyT)",
        "🩺 Analisis Tekanan & Auto-PRV (Engine: WNTR)"
    ]
)

st.sidebar.markdown("---")
st.sidebar.info("Multi-engine: EPyT + WNTR")

st.title(menu)

uploaded_file = st.file_uploader(
    "Upload file .inp EPANET",
    type=["inp"]
)

# =====================================================
# MAIN
# =====================================================

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".inp") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        # =================================================
        # FEATURE 1 : AUTO SOLVER
        # =================================================
        if menu == "🚀 Auto-Solver (Engine: EPyT)":
            st.write(
                "🔧 Optimasi diameter otomatis berdasarkan "
                "kecepatan aliran (target 0.5–2.0 m/s)"
            )

            d = None
            try:
                d = epanet(tmp_path)
                link_ids = d.getLinkNameID()
                diameter_awal = d.getLinkDiameter()

                standar_pipa = [50, 75, 100, 150, 200, 250, 300, 400, 500, 600, 800]

                # Iterasi optimasi
                for iterasi in range(5):
                    st.info(f"Iterasi optimasi {iterasi+1}/5")
                    
                    d.openHydraulicAnalysis()
                    d.runHydraulicAnalysis()
                    d.closeHydraulicAnalysis()

                    velocity = d.getLinkVelocity()

                    for i in range(len(link_ids)):
                        v = abs(velocity[i])
                        d_now = d.getLinkDiameter(i + 1)
                        d_new = d_now

                        if 0.001 < v < 0.5:
                            kandidat = [x for x in standar_pipa if x < d_now]
                            if kandidat:
                                d_new = max(kandidat)
                        elif v > 2.0:
                            kandidat = [x for x in standar_pipa if x > d_now]
                            if kandidat:
                                d_new = min(kandidat)

                        if d_new != d_now:
                            d.setLinkDiameter(i + 1, d_new)

                # Run final
                d.openHydraulicAnalysis()
                d.runHydraulicAnalysis()
                d.closeHydraulicAnalysis()

                final_velocity = d.getLinkVelocity()

                hasil = []
                berubah = 0

                for i in range(len(link_ids)):
                    awal = diameter_awal[i]
                    akhir = d.getLinkDiameter(i + 1)

                    if akhir > awal:
                        status = "Diperbesar"
                    elif akhir < awal:
                        status = "Diperkecil"
                    else:
                        status = "Tetap"

                    if awal != akhir:
                        berubah += 1

                    hasil.append({
                        "ID Pipa": link_ids[i],
                        "Diameter Awal": f"{awal:.0f} mm",
                        "Diameter Baru": f"{akhir:.0f} mm",
                        "Velocity": f"{abs(final_velocity[i]):.3f} m/s",
                        "Status": status
                    })

                df = pd.DataFrame(hasil)

                st.markdown("### 📊 Ringkasan Optimasi")
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Pipa", len(link_ids))
                c2.metric("Diubah", berubah)
                c3.metric("Engine", "EPyT ✅")

                st.dataframe(
                    df.style.map(warnai_status_solver, subset=["Status"]),
                    use_container_width=True,
                    height=400
                )

                # Download hasil
                new_inp = tmp_path.replace(".inp", "_optimized.inp")
                d.saveInputFile(new_inp)

                with open(new_inp, "rb") as file:
                    st.download_button(
                        "💾 Unduh File Optimasi",
                        data=file,
                        file_name="Jaringan_Optimasi.inp",
                        mime="text/plain"
                    )

            finally:
                if d:
                    d.unload()

        # =================================================
        # FEATURE 2 : ANALISIS TEKANAN + PRV
        # =================================================
        elif menu == "🩺 Analisis Tekanan & Auto-PRV (Engine: WNTR)":
            st.write("🔍 Analisis tekanan dan pencarian kombinasi terbaik Triple PRV.")

            # Clean file
            with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            with open(tmp_path, "w", encoding="utf-8") as f:
                skip = False
                for line in lines:
                    u = line.strip().upper()
                    if u == "[LEAKAGE]":
                        skip = True
                        continue
                    if skip and line.startswith("["):
                        skip = False
                    if "BACKFLOW ALLOWED" in u:
                        continue
                    if not skip:
                        f.write(line)

            wn = wntr.network.WaterNetworkModel(tmp_path)
            sim = wntr.sim.EpanetSimulator(wn)
            results = sim.run_sim()
            
            # PERBAIKAN: Akses timestep pertama dengan benar
            tekanan_awal = results.node["pressure"].iloc[0]

            # Diagnosis awal
            data_awal = []
            low_pressure = 0
            high_pressure = 0
            
            for node in wn.junction_name_list:
                p = tekanan_awal[node]
                if pd.isna(p) or p < -100:
                    p = 0
                    status = "Error"
                elif p < 15:
                    status = "Terlalu Rendah"
                    low_pressure += 1
                elif p > 80:
                    status = "Bahaya (Terlalu Tinggi)"
                    high_pressure += 1
                else:
                    status = "Aman"
                
                data_awal.append({
                    "Node": node,
                    "Tekanan": round(p, 2),
                    "Status": status
                })

            df_awal = pd.DataFrame(data_awal)
            st.markdown("### 📈 Diagnosis Tekanan Awal")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Rendah (<15m)", low_pressure)
            col2.metric("Tinggi (>80m)", high_pressure)
            col3.metric("Total Node", len(wn.junction_name_list))
            
            st.dataframe(
                df_awal.style.map(warnai_status_tekanan, subset=["Status"]),
                use_container_width=True,
                height=400
            )

            st.markdown("### 🗺️ Peta Jaringan Awal")
            tampilkan_network(wn, tekanan_awal, "Tekanan Awal Network")
            st.markdown("---")

            setting_prv = st.number_input("🎯 Target tekanan PRV (m)", min_value=10.0, max_value=100.0, value=50.0)

            if st.button("🚀 Cari Kombinasi Triple PRV Terbaik", type="primary"):
                kandidat_pipa = [p for p in wn.pipe_name_list if wn.get_link(p).diameter > 0.15]
                
                if len(kandidat_pipa) < 3:
                    st.error("❌ Tidak cukup pipa kandidat untuk Triple PRV!")
                else:
                    combos = list(combinations(kandidat_pipa, 3))
                    total = len(combos)
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    best_score = -1
                    best_combo = None
                    best_result = None
                    best_network = None

                    with st.spinner(f"🔍 Menganalisis {total} kombinasi..."):
                        for idx, combo in enumerate(combos):
                            progress_bar.progress((idx + 1) / total)
                            status_text.text(f"Testing: {combo[0]}, {combo[1]}, {combo[2]}")
                            
                            try:
                                wn_test = wntr.network.WaterNetworkModel(tmp_path)
                                for pipe_name in combo:
                                    pipe = wn_test.get_link(pipe_name)
                                    wn_test.remove_link(pipe_name)
                                    wn_test.add_valve(f"PRV_{pipe_name}", 
                                                    pipe.start_node_name, 
                                                    pipe.end_node_name, 
                                                    diameter=pipe.diameter,
                                                    valve_type="PRV", 
                                                    initial_setting=setting_prv)

                                sim_test = wntr.sim.EpanetSimulator(wn_test)
                                res = sim_test.run_sim()
                                tekanan = res.node["pressure"].iloc[0]

                                # Skip hasil absurd
                                if any(pd.isna(tekanan[n]) or tekanan[n] < -100 for n in wn_test.junction_name_list):
                                    continue

                                aman = sum(1 for n in wn_test.junction_name_list 
                                         if 15 <= tekanan[n] <= 80)

                                if aman > best_score:
                                    best_score = aman
                                    best_combo = combo
                                    best_result = tekanan
                                    best_network = wn_test

                            except Exception:
                                continue

                    progress_bar.empty()
                    status_text.empty()

                    if best_combo:
                        st.success(f"✅ **Kombinasi Terbaik Ditemukan!**")
                        st.info(f"🎯 Pasang PRV di pipa: **{', '.join(best_combo)}**")
                        st.balloons()
                        
                        st.metric("Node Aman", f"{best_score}/{len(wn.junction_name_list)}", f"{best_score/len(wn.junction_name_list)*100:.1f}%")

                        # Perbandingan
                        compare = []
                        for node in wn.junction_name_list:
                            old_p = tekanan_awal[node]
                            new_p = best_result[node]
                            p_tampil = new_p if (pd.notna(new_p) and new_p > -100) else 0

                            if p_tampil < 15:
                                status = "Terlalu Rendah"
                            elif p_tampil > 80:
                                status = "Bahaya (Terlalu Tinggi)"
                            else:
                                status = "Aman"

                            compare.append({
                                "Node": node,
                                "Tekanan Lama": round(old_p, 2),
                                "Tekanan Baru": round(p_tampil, 2),
                                "Status": status
                            })

                        df2 = pd.DataFrame(compare)
                        st.markdown("### 📊 Perbandingan Tekanan")
                        st.dataframe(
                            df2.style.map(warnai_status_tekanan, subset=["Status"]),
                            use_container_width=True,
                            height=400
                        )

                        st.markdown("### 🗺️ Peta Jaringan Setelah Triple PRV")
                        tampilkan_network(best_network, best_result, "Tekanan Setelah Triple PRV")

                        # Download file
                        new_inp = tmp_path.replace(".inp", "_TriplePRV.inp")
                        wntr.network.write_inpfile(best_network, new_inp)
                        with open(new_inp, "rb") as file:
                            st.download_button(
                                "💾 Unduh File Triple PRV",
                                data=file,
                                file_name="Jaringan_Triple_PRV.inp",
                                mime="text/plain"
                            )
                    else:
                        st.error("❌ Tidak ditemukan kombinasi PRV yang valid.")
                        st.info("💡 Coba ubah target tekanan PRV atau periksa model jaringan.")

    except Exception as e:
        st.error(f"❌ Gagal menjalankan analisis: {str(e)}")
        st.exception(e)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass
