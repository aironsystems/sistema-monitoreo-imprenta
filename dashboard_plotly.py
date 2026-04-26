import sqlite3
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from flask import Flask
import json

app = Flask(__name__)

def cargar_datos():
    con = sqlite3.connect('imprenta.db')
    produccion = pd.read_sql_query(
        "SELECT fecha_hora, ejemplares, velocidad_rpm, eficiencia, estado_linea FROM produccion ORDER BY fecha_hora DESC LIMIT 100",
        con
    )
    estados = pd.read_sql_query(
        "SELECT fecha_hora, motor_principal, motor_entintado, motor_humedad, nivel_tinta, nivel_humedad, diametro_rollo, rollo_activo FROM estados ORDER BY fecha_hora DESC LIMIT 100",
        con
    )
    alarmas = pd.read_sql_query(
        "SELECT fecha_hora, tipo, descripcion FROM alarmas ORDER BY fecha_hora DESC LIMIT 15",
        con
    )
    fallas = pd.read_sql_query(
        "SELECT tipo_falla, componente, duracion_segundos, resuelta FROM fallas ORDER BY fecha_inicio DESC LIMIT 10",
        con
    )
    con.close()
    return produccion, estados, alarmas, fallas

def generar_graficos(produccion, estados):
    prod_ord = produccion.iloc[::-1].reset_index(drop=True)
    est_ord  = estados.iloc[::-1].reset_index(drop=True)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Produccion por ciclo",
            "Eficiencia de linea (%)",
            "Niveles de Tinta y Humedad (%)",
            "Velocidad del motor principal (RPM)"
        ),
        vertical_spacing=0.15,
        horizontal_spacing=0.1
    )

    # Gráfico 1 — Producción
    fig.add_trace(go.Scatter(
        x=prod_ord["fecha_hora"],
        y=prod_ord["ejemplares"],
        mode="lines+markers",
        name="Ejemplares",
        line=dict(color="#3498DB", width=2),
        marker=dict(size=5)
    ), row=1, col=1)

    # Gráfico 2 — Eficiencia
    colores_efic = ["#E74C3C" if e < 90 else "#2ECC71" for e in prod_ord["eficiencia"].fillna(100)]
    fig.add_trace(go.Bar(
        x=prod_ord["fecha_hora"],
        y=prod_ord["eficiencia"],
        name="Eficiencia %",
        marker_color=colores_efic
    ), row=1, col=2)

    # Línea de referencia 90%
    fig.add_hline(y=90, line_dash="dash", line_color="#F39C12",
                  annotation_text="Umbral 90%", row=1, col=2)

    # Gráfico 3 — Tinta y Humedad
    fig.add_trace(go.Scatter(
        x=est_ord["fecha_hora"],
        y=est_ord["nivel_tinta"],
        mode="lines",
        name="Tinta %",
        line=dict(color="#E74C3C", width=2)
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=est_ord["fecha_hora"],
        y=est_ord["nivel_humedad"],
        mode="lines",
        name="Humedad %",
        line=dict(color="#2ECC71", width=2)
    ), row=2, col=1)

    # Gráfico 4 — Velocidad RPM
    fig.add_trace(go.Scatter(
        x=prod_ord["fecha_hora"],
        y=prod_ord["velocidad_rpm"],
        mode="lines",
        name="RPM",
        line=dict(color="#9B59B6", width=2),
        fill="tozeroy",
        fillcolor="rgba(155,89,182,0.1)"
    ), row=2, col=2)

    fig.add_hline(y=1100, line_dash="dash", line_color="#E74C3C",
                  annotation_text="RPM critico", row=2, col=2)

    fig.update_layout(
        height=600,
        paper_bgcolor="#1A1A2E",
        plot_bgcolor="#16213E",
        font=dict(color="#E0E0E0", family="Arial"),
        showlegend=True,
        legend=dict(bgcolor="#16213E", bordercolor="#2D2D4E"),
        margin=dict(t=60, b=40, l=40, r=40)
    )

    for i in fig.layout.annotations:
        i.font.color = "#A0A0A0"

    fig.update_xaxes(showgrid=False, tickfont=dict(color="#A0A0A0"))
    fig.update_yaxes(gridcolor="#2D2D4E", tickfont=dict(color="#A0A0A0"))

    return fig.to_json()

@app.route("/")
def index():
    from datetime import datetime
    from indicadores import calcular_mtbf_mttr

    produccion, estados, alarmas, fallas = cargar_datos()
    ind = calcular_mtbf_mttr()

    # Indicadores de motor
    if not estados.empty:
        ultimo = estados.iloc[0]
        mp = int(ultimo["motor_principal"])
        me = int(ultimo["motor_entintado"])
        mh = int(ultimo["motor_humedad"])
        di = float(ultimo["diametro_rollo"]) if ultimo["diametro_rollo"] else 0
        ra = int(ultimo["rollo_activo"]) if ultimo["rollo_activo"] else 1
    else:
        mp = me = mh = ra = 0
        di = 0

    def cm(v): return "#2ECC71" if v == 1 else "#E74C3C"
    def tm(v): return "ACTIVO" if v == 1 else "INACTIVO"
    cd = "#F39C12" if di < 910 else "#2ECC71"

    # Indicadores KPI
    mtbf_txt = f"{ind['mtbf']:.0f} seg"        if ind["mtbf"]           else "Sin datos"
    mttr_txt = f"{ind['mttr']:.0f} seg"         if ind["mttr"]           else "Sin datos"
    disp_txt = f"{ind['disponibilidad']}%"       if ind["disponibilidad"] else "Sin datos"
    efic_txt = f"{ind['eficiencia_global']}%"
    color_disp = "#2ECC71" if ind["disponibilidad"] and ind["disponibilidad"] >= 85 else "#E74C3C" if ind["disponibilidad"] else "#A0A0A0"

    # Gráficos
    graficos_json = generar_graficos(produccion, estados) if not produccion.empty else "null"

    # Tabla de alarmas
    filas_alarmas = ""
    if not alarmas.empty:
        for _, a in alarmas.iterrows():
            c = "#E74C3C" if a["tipo"] in ["ALERTA", "CRITICO"] else "#F39C12" if a["tipo"] == "AVISO" else "#3498DB"
            filas_alarmas += (
                "<tr>"
                "<td style='color:#A0A0A0;padding:8px;font-size:12px'>" + str(a["fecha_hora"]) + "</td>"
                "<td style='color:" + c + ";padding:8px;font-weight:bold;font-size:12px'>" + str(a["tipo"]) + "</td>"
                "<td style='color:#E0E0E0;padding:8px;font-size:12px'>" + str(a["descripcion"]) + "</td>"
                "</tr>"
            )
    if not filas_alarmas:
        filas_alarmas = "<tr><td colspan='3' style='color:#A0A0A0;padding:8px'>Sin alarmas registradas.</td></tr>"

    ts = datetime.now().strftime("%H:%M:%S")

    paneles_motor = (
        "<div class='panel'><p>Motor Principal</p><h2 style='color:" + cm(mp) + "'>" + tm(mp) + "</h2></div>"
        "<div class='panel'><p>Motor Entintado</p><h2 style='color:" + cm(me) + "'>" + tm(me) + "</h2></div>"
        "<div class='panel'><p>Motor Humedad</p><h2 style='color:"  + cm(mh) + "'>" + tm(mh) + "</h2></div>"
        "<div class='panel'><p>Rollo Activo</p><h2 style='color:#3498DB'>ROLLO " + str(ra) + "</h2></div>"
        "<div class='panel'><p>Diametro</p><h2 style='color:" + cd + "'>" + str(di) + " mm</h2></div>"
    )

    paneles_kpi = (
        "<div class='panel'><p>MTBF</p><h2 style='color:#3498DB'>" + mtbf_txt + "</h2></div>"
        "<div class='panel'><p>MTTR</p><h2 style='color:#F39C12'>" + mttr_txt + "</h2></div>"
        "<div class='panel'><p>Disponibilidad</p><h2 style='color:" + color_disp + "'>" + disp_txt + "</h2></div>"
        "<div class='panel'><p>Efic. Global</p><h2 style='color:#2ECC71'>" + efic_txt + "</h2></div>"
        "<div class='panel'><p>Total Fallas</p><h2 style='color:#E74C3C'>" + str(ind["total_fallas"]) + "</h2></div>"
    )

    return (
        "<!DOCTYPE html><html><head><meta charset='UTF-8'>"
        "<meta http-equiv='refresh' content='5'>"
        "<title>Monitor Imprenta Offset</title>"
        "<script src='https://cdn.plot.ly/plotly-2.27.0.min.js'></script>"
        "<style>"
        "*{margin:0;padding:0;box-sizing:border-box;font-family:Arial,sans-serif}"
        "body{background:#1A1A2E;color:#E0E0E0;padding:20px}"
        "h1{text-align:center;margin-bottom:6px;font-size:22px}"
        "h3{color:#A0A0A0;font-size:13px;margin-bottom:10px}"
        ".sub{text-align:center;color:#A0A0A0;font-size:13px;margin-bottom:20px}"
        ".row{display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap}"
        ".panel{flex:1;min-width:120px;background:#16213E;border-radius:10px;padding:16px;text-align:center}"
        ".panel p{color:#A0A0A0;font-size:12px;margin-bottom:6px}"
        ".panel h2{font-size:18px}"
        ".box{background:#16213E;border-radius:10px;padding:20px;margin-bottom:16px}"
        "table{width:100%;border-collapse:collapse}"
        ".ts{text-align:center;color:#555;font-size:11px;margin-top:12px}"
        "</style></head><body>"
        "<h1>Sistema de Monitoreo — Imprenta Offset</h1>"
        "<p class='sub'>Ultima actualizacion: " + ts + " — Recarga automatica cada 5 segundos</p>"
        "<div class='row'>" + paneles_motor + "</div>"
        "<div class='row'>" + paneles_kpi   + "</div>"
        "<div class='box'><div id='graficos'></div></div>"
        "<div class='box'><h3>ULTIMAS ALARMAS Y EVENTOS</h3><table>" + filas_alarmas + "</table></div>"
        "<script>"
        "var fig = " + graficos_json + ";"
        "if(fig){ Plotly.newPlot('graficos', fig.data, fig.layout, {responsive:true, displaylogo:false}); }"
        "</script>"
        "</body></html>"
    )

if __name__ == "__main__":
    print("Dashboard Plotly iniciado.")
    print("Abri tu navegador en: http://127.0.0.1:8051")
    app.run(debug=False, port=8051)