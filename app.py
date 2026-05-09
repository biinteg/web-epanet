import streamlit as st
from epyt import epanet
import tempfile
import os
import pandas as pd

st.set_page_config(page_title="EPANET Pressure Analyzer", layout="wide")

st.title("Pemindai Tekanan Jaringan (Pressure Analyzer) 🩺")
st.write("Sistem ini mendiagnosis kesehatan tekanan air di setiap Node (Titik) pada jaringan Anda.")

uploaded_file = st.file_uploader("Upload File .inp EPANET", type=['inp'])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".inp") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        d = epanet(tmp_path)
        
        # --- JALANKAN MESIN HIDROLIKA ---
        d.openHydraulicAnalysis()
        d.initializeHydraulicAnalysis(0)
        d.runHydraulicAnalysis()
        
        # --- AMBIL DATA NODE ---
        node_ids = d.getNodeNameID()
        elevations = d.getNodeElevations()
        pressures = d.getNodePressure() # Ini data sakti yang kita cari!
        
        d.closeHydraulicAnalysis() 
        
        data_tabel = []
        node_rendah = 0
        node_aman = 0
        node_tinggi = 0

        # Kita hitung khusus untuk Node biasa (Junction), bukan Reservoir/Tank
        # Reservoir biasanya ada di index terakhir, tapi kita filter pakai tipe node (jika perlu)
        # Untuk amannya, kita analisis semua node dulu.
        
        for i in range(len(node_ids)):
            p = pressures[i]
            elev = elevations[i]
            
            # Abaikan Reservoir (Biasanya tekanannya 0 di pembacaan EPyT jika bukan Junction)
            if "Res" in node_ids[i] or elev == 0:
                continue
                
            status_p = "Aman"
            
            # Standar Tekanan SPAM Perumahan (15m - 80m)
            if p < 15:
                status_p = "Terlalu Rendah"
                node_rendah += 1
            elif p > 80:
                status_p = "Bahaya (Terlalu Tinggi)"
                node_tinggi += 1
            else:
                node_aman += 1

            data_tabel.append({
                "ID Node": node_ids[i],
                "Elevasi Tanah (m)": round(elev, 2),
                "Tekanan / Pressure (m)": round(p, 2),
                "Status": status_p
            })

        # --- TAMPILAN DASHBOARD ---
        st.markdown("### Ringkasan Kesehatan Node")
        col1, col2, col3 = st.columns(3)
        col1.metric("Node Tekanan Rendah (< 15m)", node_rendah)
        col2.metric("Node Aman (15m - 80m)", node_aman)
        col3.metric("Node Bahaya Meledak (> 80m)", node_tinggi)

        st.markdown("### Laporan Detail Tekanan")
        df = pd.DataFrame(data_tabel)
        
        # Logika Pewarnaan Tabel
        def warnai_status(val):
            if val == 'Aman':
                color = 'green'
            elif val == 'Terlalu Rendah':
                color = 'orange'
            else:
                color = 'red'
            return f'color: {color}'
            
        st.dataframe(df.style.map(warnai_status, subset=['Status']), use_container_width=True)

    except Exception as e:
        st.error(f"Gagal menjalankan analisis: {e}")
        
    finally:
        d.unload()
        os.remove(tmp_path)
