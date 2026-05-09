import streamlit as st
from epyt import epanet
import tempfile
import os

st.title("Aplikasi Web Analisis EPANET 💧")
st.write("Silakan upload file .inp hasil export dari EPANET.")

uploaded_file = st.file_uploader("Upload File .inp", type=['inp'])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".inp") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        st.info("Sedang memuat jaringan...")
        d = epanet(tmp_path) 
        st.success("File .inp berhasil dibaca oleh EPyT!")

        st.subheader("Ringkasan Jaringan:")
        st.write(f"🔹 Jumlah Node/Persimpangan: **{d.getNodeCount()}**")
        st.write(f"🔹 Jumlah Pipa: **{d.getLinkCount()}**")
        st.write(f"🔹 Jumlah Tangki/Reservoir: **{d.getNodeTankCount()}**")

    except Exception as e:
        st.error(f"Terjadi kesalahan hidrolika: {e}")
        
    finally:
        d.unload()
        os.remove(tmp_path)
