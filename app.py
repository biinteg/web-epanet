import streamlit as st
from epyt import epanet
import wntr
import tempfile
import os
import pandas as pd
from itertools import combinations

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

if uploaded_file is not None:

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".inp"
    ) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:

        # =====================================================
        # FEATURE 1: AUTO SOLVER
        # =====================================================
        if menu == "🚀 Auto-Solver (Engine: EPyT)":

            st.write(
                "Optimasi diameter otomatis berdasarkan "
                "kecepatan aliran (target 0.5–2.0 m/s)"
            )

            d = None

            try:
                d = epanet(tmp_path)

                link_ids = d.getLinkNameID()
                diams_asli = d.getLinkDiameter()

                standar_pipa = [
                    50, 75, 100, 150, 200,
                    250, 300, 400, 500, 600, 800
                ]

                # Iterative optimization
                for iteration in range(5):

                    d.openHydraulicAnalysis()
                    d.initializeHydraulicAnalysis(0)
                    d.runHydraulicAnalysis()

                    velocities = d.getLinkVelocity()

                    d.closeHydraulicAnalysis()

                    for i in range(len(link_ids)):
                        v = abs(velocities[i])
                        current_d = d.getLinkDiameter(i + 1)

                        new_d = current_d

                        if v < 0.5 and v > 0.001:
                            smaller = [
                                x for x in standar_pipa
                                if x < current_d
                            ]
                            if smaller:
                                new_d = max(smaller)

                        elif v > 2.0:
                            larger = [
                                x for x in standar_pipa
                                if x > current_d
                            ]
                            if larger:
                                new_d = min(larger)

                        d.setLinkDiameter(i + 1, new_d)

                # Final run
                d.openHydraulicAnalysis()
                d.initializeHydraulicAnalysis(0)
                d.runHydraulicAnalysis()
                final_vel = d.getLinkVelocity()
                d.closeHydraulicAnalysis()

                data = []
                changed = 0

                for i in range(len(link_ids)):
                    original = diams_asli[i]
                    optimized = d.getLinkDiameter(i + 1)

                    if optimized > original:
                        status = "Diperbesar"
                    elif optimized < original:
                        status = "Diperkecil"
                    else:
                        status = "Tetap"

                    if optimized != original:
                        changed += 1

                    data.append({
                        "ID Pipa": link_ids[i],
                        "Diameter Asli (mm)": original,
                        "Diameter Baru (mm)": optimized,
                        "Velocity (m/s)": round(abs(final_vel[i]), 3),
                        "Status": status
                    })

                st.markdown("### Ringkasan")

                c1, c2, c3 = st.columns(3)

                c1.metric("Total Pipa", len(link_ids))
                c2.metric("Diubah", changed)
                c3.metric("Engine", "EPyT ✅")

                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)

                # Save optimized inp
                new_inp = tmp_path.replace(
                    ".inp",
                    "_optimized.inp"
                )

                d.saveInputFile(new_inp)

                with open(new_inp, "rb") as file:
                    st.download_button(
                        "Unduh File Optimasi",
                        data=file,
                        file_name="Jaringan_Optimasi.inp",
                        mime="text/plain"
                    )

            finally:
                if d:
                    d.unload()

        # =====================================================
        # FEATURE 2: PRESSURE + AUTO PRV
        # =====================================================
        elif menu == "🩺 Analisis Tekanan & Auto-PRV (Engine: WNTR)":

            st.write(
                "Analisis tekanan dan pencarian "
                "lokasi terbaik 3 PRV."
            )

            # -----------------------------------------
            # CLEAN FILE
            # -----------------------------------------
            with open(
                tmp_path,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as f:
                lines = f.readlines()

            with open(
                tmp_path,
                "w",
                encoding="utf-8"
            ) as f:
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

            tekanan_awal = results.node["pressure"].loc[0]

            # -----------------------------------------
            # INITIAL PRESSURE TABLE
            # -----------------------------------------
            data = []

            for node in wn.junction_name_list:
                p = tekanan_awal[node]

                if p < 15:
                    status = "Terlalu Rendah"
                elif p > 80:
                    status = "Terlalu Tinggi"
                else:
                    status = "Aman"

                data.append({
                    "Node": node,
                    "Tekanan": round(p, 2),
                    "Status": status
                })

            df = pd.DataFrame(data)

            st.markdown("### Diagnosis Tekanan")
            st.dataframe(df, use_container_width=True)

            # -----------------------------------------
            # PRV SEARCH
            # -----------------------------------------
            st.markdown("---")

            setting_prv = st.number_input(
                "Target tekanan PRV (m)",
                min_value=10.0,
                max_value=100.0,
                value=50.0
            )

            if st.button("Cari Kombinasi Triple PRV 🚀"):

                candidate_pipes = []

                for p in wn.pipe_name_list:
                    pipe = wn.get_link(p)

                    if pipe.diameter > 0.15:
                        candidate_pipes.append(p)

                combos = list(
                    combinations(candidate_pipes, 3)
                )

                total = len(combos)

                progress = st.progress(0)

                best_score = -1
                best_combo = None
                best_result = None
                best_network = None

                with st.spinner(
                    "Mencari konfigurasi terbaik..."
                ):

                    for idx, combo in enumerate(combos):

                        progress.progress(
                            (idx + 1) / total
                        )

                        try:
                            wn_test = wntr.network.WaterNetworkModel(
                                tmp_path
                            )

                            for pipe_name in combo:
                                pipe = wn_test.get_link(
                                    pipe_name
                                )

                                wn_test.remove_link(
                                    pipe_name
                                )

                                wn_test.add_valve(
                                    f"PRV_{pipe_name}",
                                    pipe.start_node_name,
                                    pipe.end_node_name,
                                    diameter=pipe.diameter,
                                    valve_type="PRV",
                                    initial_setting=setting_prv
                                )

                            sim_test = wntr.sim.EpanetSimulator(
                                wn_test
                            )

                            res = sim_test.run_sim()

                            tekanan = res.node[
                                "pressure"
                            ].loc[0]

                            aman = sum(
                                1
                                for n in wn_test.junction_name_list
                                if 15 <= tekanan[n] <= 80
                            )

                            if aman > best_score:
                                best_score = aman
                                best_combo = combo
                                best_result = tekanan
                                best_network = wn_test

                            if aman == len(
                                wn_test.junction_name_list
                            ):
                                break

                        except Exception:
                            continue

                # -------------------------------------
                # SHOW RESULT
                # -------------------------------------
                if best_combo:

                    st.success(
                        f"Pasang PRV di: "
                        f"{best_combo[0]}, "
                        f"{best_combo[1]}, "
                        f"{best_combo[2]}"
                    )

                    st.info(
                        f"Node aman: "
                        f"{best_score} "
                        f"dari "
                        f"{len(wn.junction_name_list)}"
                    )

                    compare = []

                    for node in wn.junction_name_list:
                        old_p = tekanan_awal[node]
                        new_p = best_result[node]

                        if new_p < 15:
                            status = "Terlalu Rendah"
                        elif new_p > 80:
                            status = "Terlalu Tinggi"
                        else:
                            status = "Aman"

                        compare.append({
                            "Node": node,
                            "Tekanan Lama": round(
                                old_p, 2
                            ),
                            "Tekanan Baru": round(
                                new_p, 2
                            ),
                            "Status": status
                        })

                    df2 = pd.DataFrame(compare)
                    def warnai_status(val):
                        if val == "Aman":
                            return "color: limegreen; font-weight: bold;"
                        else:
                            return "color: red; font-weight: bold;"

                    st.dataframe(
                        df2.style.map(
                            warnai_status,
                            subset=["Status"]
                        ),
                        use_container_width=True
                    )
                    
                    # save new network
                    new_inp = tmp_path.replace(
                        ".inp",
                        "_TriplePRV.inp"
                    )

                    wntr.network.write_inpfile(
                        best_network,
                        new_inp
                    )

                    with open(
                        new_inp,
                        "rb"
                    ) as file:
                        st.download_button(
                            "Unduh File Triple PRV",
                            data=file,
                            file_name="Jaringan_Triple_PRV.inp",
                            mime="text/plain"
                        )

                else:
                    st.error(
                        "Tidak ditemukan kombinasi cocok."
                    )

    except Exception as e:
        st.error(
            f"Gagal menjalankan analisis: {e}"
        )

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
