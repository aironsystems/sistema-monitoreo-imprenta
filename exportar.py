import sqlite3
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import os

def conectar():
    return sqlite3.connect('imprenta.db')

# ── Exportar CSV ──────────────────────────────────────────────────────────────
def exportar_csv():
    con = conectar()

    produccion = pd.read_sql_query(
        "SELECT * FROM produccion ORDER BY fecha_hora ASC", con)
    estados = pd.read_sql_query(
        "SELECT * FROM estados ORDER BY fecha_hora ASC", con)
    alarmas = pd.read_sql_query(
        "SELECT * FROM alarmas ORDER BY fecha_hora ASC", con)
    fallas = pd.read_sql_query(
        "SELECT * FROM fallas ORDER BY fecha_inicio ASC", con)
    con.close()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("exportaciones", exist_ok=True)

    produccion.to_csv(f"exportaciones/produccion_{timestamp}.csv", index=False)
    estados.to_csv(f"exportaciones/estados_{timestamp}.csv",    index=False)
    alarmas.to_csv(f"exportaciones/alarmas_{timestamp}.csv",    index=False)
    fallas.to_csv(f"exportaciones/fallas_{timestamp}.csv",      index=False)

    print(f"CSV exportados en carpeta exportaciones/")
    print(f"  produccion_{timestamp}.csv  — {len(produccion)} registros")
    print(f"  estados_{timestamp}.csv     — {len(estados)} registros")
    print(f"  alarmas_{timestamp}.csv     — {len(alarmas)} registros")
    print(f"  fallas_{timestamp}.csv      — {len(fallas)} registros")

    return timestamp

# ── Generar reporte HTML ──────────────────────────────────────────────────────
def generar_reporte_html(timestamp=None):
    con = conectar()

    produccion = pd.read_sql_query(
        "SELECT fecha_hora, ejemplares, velocidad_rpm, eficiencia, estado_linea FROM produccion ORDER BY fecha_hora ASC",
        con)
    estados = pd.read_sql_query(
        "SELECT fecha_hora, nivel_tinta, nivel_humedad, diametro_rollo FROM estados ORDER BY fecha_hora ASC",
        con)
    alarmas = pd.read_sql_query(
        "SELECT fecha_hora, tipo, descripcion FROM alarmas ORDER BY fecha_hora DESC LIMIT 20",
        con)
    fallas = pd.read_sql_query(
        "SELECT tipo_falla, componente, duracion_segundos, resuelta, fecha_inicio FROM fallas ORDER BY fecha_inicio DESC",
        con)

    cur = con.cursor()
    cur.execute("SELECT COUNT(*), SUM(ejemplares), AVG(eficiencia) FROM produccion")
    totales = cur.fetchone()
    cur.execute("SELECT COUNT(*) FROM fallas WHERE resuelta=1")
    fallas_resueltas = cur.fetchone()[0]
    cur.execute("SELECT AVG(duracion_segundos) FROM fallas WHERE resuelta=1")
    mttr = cur.fetchone()[0]
    con.close()

    # Gráficos
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Produccion por ciclo",
            "Eficiencia de linea (%)",
            "Niveles de Tinta y Humedad",
            "Velocidad RPM"
        ),
        vertical_spacing=0.2
    )

    fig.add_trace(go.Scatter(
        x=produccion["fecha_hora"], y=produccion["ejemplares"],
        mode="lines", name="Ejemplares",
        line=dict(color="#3498DB", width=2)
    ), row=1, col=1)

    colores = ["#E74C3C" if e and e < 90 else "#2ECC71"
               for e in produccion["eficiencia"]]
    fig.add_trace(go.Bar(
        x=produccion["fecha_hora"], y=produccion["eficiencia"],
        name="Eficiencia", marker_color=colores
    ), row=1, col=2)
    fig.add_hline(y=90, line_dash="dash", line_color="#F39C12", row=1, col=2)

    fig.add_trace(go.Scatter(
        x=estados["fecha_hora"], y=estados["nivel_tinta"],
        mode="lines", name="Tinta %",
        line=dict(color="#E74C3C", width=2)
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=estados["fecha_hora"], y=estados["nivel_humedad"],
        mode="lines", name="Humedad %",
        line=dict(color="#2ECC71", width=2)
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=produccion["fecha_hora"], y=produccion["velocidad_rpm"],
        mode="lines", name="RPM",
        line=dict(color="#9B59B6", width=2),
        fill="tozeroy", fillcolor="rgba(155,89,182,0.1)"
    ), row=2, col=2)
    fig.add_hline(y=1100, line_dash="dash", line_color="#E74C3C", row=2, col=2)

    fig.update_layout(
        height=600,
        paper_bgcolor="#1A1A2E",
        plot_bgcolor="#16213E",
        font=dict(color="#E0E0E0"),
        margin=dict(t=60, b=40, l=40, r=40)
    )
    fig.update_xaxes(showgrid=False, tickfont=dict(color="#A0A0A0"))
    fig.update_yaxes(gridcolor="#2D2D4E", tickfont=dict(color="#A0A0A0"))

    graficos_html = fig.to_html(full_html=False, include_plotlyjs="cdn")

    # Tabla de alarmas
    filas_alarmas = ""
    for _, a in alarmas.iterrows():
        c = "#E74C3C" if a["tipo"] in ["ALERTA","CRITICO"] else "#F39C12" if a["tipo"]=="AVISO" else "#3498DB"
        filas_alarmas += (
            f"<tr>"
            f"<td style='padding:8px;color:#A0A0A0'>{a['fecha_hora']}</td>"
            f"<td style='padding:8px;color:{c};font-weight:bold'>{a['tipo']}</td>"
            f"<td style='padding:8px;color:#E0E0E0'>{a['descripcion']}</td>"
            f"</tr>"
        )

    # Tabla de fallas
    filas_fallas = ""
    for _, f in fallas.iterrows():
        estado = "RESUELTA" if f["resuelta"] == 1 else "PENDIENTE"
        color  = "#2ECC71" if f["resuelta"] == 1 else "#E74C3C"
        dur    = f"{f['duracion_segundos']:.0f}s" if f["duracion_segundos"] else "En curso"
        filas_fallas += (
            f"<tr>"
            f"<td style='padding:8px;color:#E0E0E0'>{f['tipo_falla']}</td>"
            f"<td style='padding:8px;color:#E0E0E0'>{f['componente']}</td>"
            f"<td style='padding:8px;color:#A0A0A0'>{f['fecha_inicio']}</td>"
            f"<td style='padding:8px;color:#E0E0E0'>{dur}</td>"
            f"<td style='padding:8px;color:{color};font-weight:bold'>{estado}</td>"
            f"</tr>"
        )

    total_ej   = f"{int(totales[1]):,}" if totales[1] else "0"
    efic_prom  = f"{totales[2]:.1f}%"   if totales[2] else "0%"
    mttr_txt   = f"{mttr:.0f} seg"      if mttr       else "Sin datos"
    generado   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Reporte Imprenta Offset</title>
<style>
  body{{background:#1A1A2E;color:#E0E0E0;font-family:Arial,sans-serif;padding:30px}}
  h1{{text-align:center;color:#E0E0E0;margin-bottom:5px}}
  h2{{color:#A0A0A0;font-size:14px;text-align:center;margin-bottom:25px}}
  h3{{color:#3498DB;font-size:15px;margin:20px 0 10px 0;border-bottom:1px solid #2D2D4E;padding-bottom:6px}}
  .kpis{{display:flex;gap:15px;margin-bottom:25px;flex-wrap:wrap}}
  .kpi{{flex:1;min-width:130px;background:#16213E;border-radius:10px;padding:18px;text-align:center}}
  .kpi p{{color:#A0A0A0;font-size:12px;margin-bottom:6px}}
  .kpi h2{{font-size:22px;color:#E0E0E0;margin:0}}
  .box{{background:#16213E;border-radius:10px;padding:20px;margin-bottom:20px}}
  table{{width:100%;border-collapse:collapse}}
  th{{color:#A0A0A0;font-size:12px;text-align:left;padding:8px;border-bottom:1px solid #2D2D4E}}
  .footer{{text-align:center;color:#555;font-size:11px;margin-top:20px}}
</style>
</head>
<body>
<h1>Reporte de Produccion — Imprenta Offset</h1>
<h2>Generado: {generado}</h2>

<div class="kpis">
  <div class="kpi"><p>Total Ciclos</p><h2>{totales[0]}</h2></div>
  <div class="kpi"><p>Total Ejemplares</p><h2>{total_ej}</h2></div>
  <div class="kpi"><p>Eficiencia Promedio</p><h2>{efic_prom}</h2></div>
  <div class="kpi"><p>Fallas Resueltas</p><h2>{fallas_resueltas}</h2></div>
  <div class="kpi"><p>MTTR Promedio</p><h2>{mttr_txt}</h2></div>
</div>

<div class="box">
  <h3>Graficos de Produccion</h3>
  {graficos_html}
</div>

<div class="box">
  <h3>Ultimas Alarmas</h3>
  <table>
    <tr>
      <th>Fecha y Hora</th><th>Tipo</th><th>Descripcion</th>
    </tr>
    {filas_alarmas}
  </table>
</div>

<div class="box">
  <h3>Registro de Fallas</h3>
  <table>
    <tr>
      <th>Tipo</th><th>Componente</th><th>Fecha Inicio</th><th>Duracion</th><th>Estado</th>
    </tr>
    {filas_fallas}
  </table>
</div>

<p class="footer">Sistema de Monitoreo — Imprenta Offset | {generado}</p>
</body>
</html>"""

    os.makedirs("exportaciones", exist_ok=True)
    ts = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre = f"exportaciones/reporte_{ts}.html"

    with open(nombre, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Reporte HTML generado: {nombre}")
    return nombre

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("   EXPORTACION DE DATOS — IMPRENTA OFFSET")
    print("=" * 55)
    ts = exportar_csv()
    generar_reporte_html(ts)
    print("=" * 55)
    print("   Abrí la carpeta exportaciones/ para ver los archivos.")
    print("=" * 55)