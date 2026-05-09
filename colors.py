def warnai_status_tekanan(val):
    """Fungsi pewarnaan status tekanan"""
    if val == "Aman":
        return "color: limegreen; font-weight: bold;"
    else:
        return "color: red; font-weight: bold;"

def warnai_status_solver(val):
    """Fungsi pewarnaan status solver diameter"""
    if val == "Diperbesar":
        return "color: limegreen; font-weight: bold;"
    elif val == "Diperkecil":
        return "color: orange; font-weight: bold;"
    else:
        return "color: cyan; font-weight: bold;"
