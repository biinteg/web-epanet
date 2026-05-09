st.markdown("---")
            st.markdown("### 2. 🤖 Auto-Pilot PRV (Pencari Pipa Terbaik)")
            st.write("Sistem akan mencoba memasang PRV di SETIAP pipa satu per satu di latar belakang, lalu memilihkan lokasi PRV yang paling banyak menyelamatkan Node.")
            
            setting_prv_auto = st.number_input("Setting Target Tekanan PRV (m):", min_value=10.0, max_value=100.0, value=50.0)

            if st.button("Jalankan Auto-Pilot PRV 🚀"):
                with st.spinner('Memindai jutaan probabilitas... Komputer sedang bekerja keras!'):
                    best_pipe = None
                    best_aman_count = -1
                    best_tekanan = None
                    best_wn = None
                    
                    # Looping: Uji coba PRV di semua pipa yang ada!
                    for test_pipe in wn.pipe_name_list:
                        try:
                            # 1. Reload file bersih untuk setiap percobaan
                            wn_test = wntr.network.WaterNetworkModel(tmp_path)
                            
                            # 2. Ambil data pipa target
                            pipa_obj = wn_test.get_link(test_pipe)
                            n1 = pipa_obj.start_node_name
                            n2 = pipa_obj.end_node_name
                            d_pipa = pipa_obj.diameter
                            
                            # 3. Operasi Bedah (Ganti dengan PRV)
                            wn_test.remove_link(test_pipe)
                            wn_test.add_valve(f"PRV_{test_pipe}", n1, n2, diameter=d_pipa, valve_type='PRV', minor_loss=0.0, initial_setting=setting_prv_auto)
                            
                            # 4. Jalankan Simulasi
                            sim_test = wntr.sim.EpanetSimulator(wn_test)
                            res_test = sim_test.run_sim()
                            tekanan_test = res_test.node['pressure'].loc[0]
                            
                            # 5. Hitung Skor (Berapa Node yang jadi Aman?)
                            aman_count = 0
                            for node_name in wn_test.junction_name_list:
                                p = tekanan_test[node_name]
                                if 15 <= p <= 80:
                                    aman_count += 1
                                    
                            # 6. Simpan jika ini adalah skor tertinggi!
                            if aman_count > best_aman_count:
                                best_aman_count = aman_count
                                best_pipe = test_pipe
                                best_tekanan = tekanan_test
                                best_wn = wn_test
                        except Exception:
                            # Jika simulasi gagal di pipa ini (misal error aliran), lewati.
                            continue

                    # --- TAMPILKAN HASIL TERBAIK ---
                    if best_pipe:
                        st.success(f"✨ ALGORITMA SELESAI! Lokasi PRV Terbaik adalah di Pipa: **'{best_pipe}'**")
                        st.info(f"Pemasangan PRV di '{best_pipe}' berhasil membuat **{best_aman_count} Node** menjadi AMAN (Hijau).")
                        
                        # Tabel Hasil
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

                        # Unduh File Terbaik
                        st.markdown("#### Unduh Jaringan Sempurna")
                        new_inp_prv = tmp_path.replace(".inp", "_AutoPilot_PRV.inp")
                        wntr.network.write_inpfile(best_wn, new_inp_prv)
                        with open(new_inp_prv, "rb") as file:
                            st.download_button(label="Unduh File .INP (Sudah Ada PRV Terbaik)", data=file, file_name=f"Jaringan_PRV_di_{best_pipe}.inp", mime="text/plain")
                    else:
                        st.error("Gagal menemukan lokasi PRV yang cocok.")
