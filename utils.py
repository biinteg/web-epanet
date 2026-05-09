# utils.py
import pandas as pd
import matplotlib.pyplot as plt
import wntr
import numpy as np
import streamlit as st

def warnai_status_tekanan(val):
    if val == "Aman":
        return "color: limegreen; font-weight: bold;"
    return "color: red; font-weight: bold;"

def warnai_status_solver(val):
    colors = {"Diperbesar": "limegreen", "Diperkecil": "orange", "Tetap": "cyan"}
    return f"color: {colors.get(val, 'white')}; font-weight: bold;"

def tampilkan_network(wn, tekanan_dict=None, judul="Visualisasi Jaringan"):
    fig, ax = plt.subplots(figsize=(14, 10))
    wntr.graphics.plot_network(wn, title=judul, ax=ax, node_size=20)
    
    if tekanan_dict is not None:
        node_xy = []
        node_colors = []
        node_labels = []
        
        for node_name in wn.junction_name_list:
            node = wn.get_node(node_name)
            x, y = node.coordinates
            node_xy.append([x, y])
            p = tekanan_dict[node_name]
            p = 0 if pd.isna(p) or p < -100 else p
            
            if p < 15: color, color_text = "red", "white"
            elif p > 80: color, color_text = "orange", "black"
            else: color, color_text = "limegreen", "black"
            
            node_colors.append(color)
            node_labels.append((x, y, f"{node_name}\n{p:.1f}", color_text))
        
        if node_xy:
            node_xy = np.array(node_xy)
            ax.scatter(node_xy[:, 0], node_xy[:, 1], c=node_colors, s=200, zorder=10, edgecolors='black', linewidth=2)
            for x, y, label, color_text in node_labels:
                ax.annotate(label, (x, y), xytext=(0, 15), textcoords='offset points', ha='center', fontsize=9, fontweight='bold',
                            bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
