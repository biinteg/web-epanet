import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import wntr
import streamlit as st

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
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Plot network dasar
    wntr.graphics.plot_network(wn, title=judul, ax=ax, node_size=20)
    
    # Tambahkan scatter plot + label untuk node dengan warna berdasarkan tekanan
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
            if pd.isna(p) or p < -100:
                p = 0
            
            if p < 15:
                node_colors.append("red")
                color_text = 'white'
            elif p > 80:
                node_colors.append("orange")
                color_text = 'black'
            else:
                node_colors.append("limegreen")
                color_text = 'black'
            
            # Format label: nama node + tekanan (1 desimal)
            label = f"{node_name}\n{p:.1f}"
            node_labels.append((x, y, label, color_text))
        
        if node_xy:
            node_xy = np.array(node_xy)
            # Scatter plot dengan ukuran lebih besar
            scatter = ax.scatter(node_xy[:, 0], node_xy[:, 1], 
                                c=node_colors, s=200, zorder=10, 
                                edgecolors='black', linewidth=2,
                                alpha=0.9)
            
            # TAMBAHAN: Label angka tekanan pada setiap node
            for x, y, label, color_text in node_labels:
                ax.annotate(label, (x, y), 
                           xytext=(0, 15), textcoords='offset points',
                           ha='center', va='bottom', fontsize=9,
                           fontweight='bold', color=color_text,
                           bbox=dict(boxstyle="round,pad=0.3", 
                                   facecolor='white', alpha=0.8,
                                   edgecolor=color_text, linewidth=1),
                           zorder=11)
    
    # Colorbar atau legend
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
        ax.legend(handles=legend_elements, loc='upper right', frameon=True, fontsize=10)
    
    # Styling tambahan
    ax.set_xlabel("X (m)", fontsize=12, fontweight='bold')
    ax.set_ylabel("Y (m)", fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
