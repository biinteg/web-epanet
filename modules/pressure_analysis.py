import streamlit as st
import wntr
import pandas as pd
from itertools import combinations
from modules.helpers import warnai_status_tekanan, tampilkan_network

def run_pressure_analysis(tmp_path):
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
