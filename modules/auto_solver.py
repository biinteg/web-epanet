import streamlit as st
from epyt import epanet
import pandas as pd
from modules.helpers import warnai_status_solver

def run_auto_solver(tmp_path):
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
