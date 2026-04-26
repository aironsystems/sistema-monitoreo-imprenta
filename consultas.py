
import sqlite3
import pandas as pd
from flask import Flask, request
from datetime import datetime

app = Flask(__name__)

def conectar():
    return sqlite3.connect("imprenta.db")

CONSULTAS_RAPIDAS = [
    {"nombre": "Produccion de hoy", "sql": "SELECT fecha_hora, ejemplares, eficiencia, estado_linea FROM produccion WHERE fecha_hora >= date('now') ORDER BY fecha_hora DESC LIMIT 50"},
    {"nombre": "Ultimas 20 alarmas", "sql": "SELECT fecha_hora, tipo, descripcion FROM alarmas ORDER BY fecha_hora DESC LIMIT 20"},
    {"nombre": "Fallas registradas", "sql": "SELECT tipo_falla, componente, duracion_segundos, resuelta, fecha_inicio FROM fallas ORDER BY fecha_inicio DESC"},
    {"nombre": "Eficiencia por estado", "sql": "SELECT estado_linea, COUNT(*) as ciclos, ROUND(AVG(eficiencia),1) as efic_prom, SUM(ejemplares) as total_ej FROM produccion GROUP BY estado_linea ORDER BY efic_prom DESC"},
    {"nombre": "Historial de sesiones", "sql": "SELECT id, fecha_inicio, fecha_fin, total_ciclos, eficiencia_promedio, fallas_detectadas, resumen FROM sesiones ORDER BY fecha_inicio DESC"},
    {"nombre": "Niveles tinta y humedad", "sql": "SELECT ROUND(AVG(nivel_tinta),1) as tinta_prom, ROUND(MIN(nivel_tinta),1) as tinta_min, ROUND(AVG(nivel_humedad),1) as humedad_prom, ROUND(MIN(nivel_humedad),1) as humedad_min FROM estados"},
    {"nombre": "Cambios de rollo", "sql": "SELECT fecha_hora, descripcion FROM alarmas WHERE tipo='INFO' AND descripcion LIKE '%Cambio automatico%' ORDER BY fecha_hora DESC"},
    {"nombre": "Alertas predictivas", "sql": "SELECT fecha_hora, tipo, descripcion FROM alarmas WHERE tipo LIKE 'PRED%' ORDER BY fecha_hora DESC LIMIT 20"},
]

def ejecutar_consulta(sql):
    try:
        con = conectar()
        df = pd.read_sql_query(sql, con)
        con.close()
        return df, None
    except Exception as e:
        return None, str(e)

def tabla_html(df):
    if df is None or df.empty:
        return "<p style='color:#A0A0A0;padding:20px'>Sin resultados.</p>"
    encabezados = "".join("<th style='padding:10px;color:#A0A0A0;font-size:12px;border-bottom:1px solid #2D2D4E;text-align:left'>" + col + "</th>" for col in df.columns)
    filas = ""
    for i, (_, row) in enumerate(df.iterrows()):
        bg = "#1A1A2E" if i % 2 == 0 else "#16213E"
        celdas = "".join("<td style='padding:9px 10px;color:#E0E0E0;font-size:12px'>" + str(val) + "</td>" for val in row.values)
        filas += "<tr style='background:" + bg + "'>" + celdas + "</tr>"
    return "<p style='color:#A0A0A0;font-size:12px;margin-bottom:10px'>" + str(len(df)) + " filas encontradas</p><div style='overflow-x:auto'><table style='width:100%;border-collapse:collapse'><thead><tr>" + encabezados + "</tr></thead><tbody>" + filas + "</tbody></table></div>"

@app.route("/", methods=["GET", "POST"])
def index():
    sql_actual = ""
    resultado_html = ""
    error_html = ""
    consulta_idx = request.form.get("consulta_rapida", "")
    sql_custom = request.form.get("sql_custom", "").strip()
    if consulta_idx != "":
        try:
            sql_actual = CONSULTAS_RAPIDAS[int(consulta_idx)]["sql"]
        except Exception:
            pass
    elif sql_custom:
        sql_actual = sql_custom
    if sql_actual:
        df, error = ejecutar_consulta(sql_actual)
        if error:
            error_html = "<div style='background:#2D1010;border-radius:8px;padding:15px;color:#E74C3C;font-size:13px'>Error: " + error + "</div>"
        else:
            resultado_html = tabla_html(df)
    botones = ""
    for i, c in enumerate(CONSULTAS_RAPIDAS):
        botones += "<button type='submit' name='consulta_rapida' value='" + str(i) + "' style='background:#16213E;color:#3498DB;border:1px solid #2D2D4E;padding:8px 14px;border-radius:6px;cursor:pointer;font-size:12px;margin:4px'>" + c["nombre"] + "</button>"
    tablas_info = ""
    try:
        con = conectar()
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tablas = [r[0] for r in cur.fetchall()]
        for t in tablas:
            cur.execute("SELECT COUNT(*) FROM " + t)
            count = cur.fetchone()[0]
            tablas_info += "<span style='color:#A0A0A0;font-size:12px;margin-right:15px'>" + t + ": <strong style='color:#3498DB'>" + str(count) + "</strong> filas</span>"
        con.close()
    except Exception:
        pass
    ts = datetime.now().strftime("%H:%M:%S")
    res_block = "<div class='box'><h3>RESULTADO</h3>" + resultado_html + "</div>" if resultado_html else ""
    return ("<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Consultas SQL</title>"
        "<style>*{margin:0;padding:0;box-sizing:border-box;font-family:Arial,sans-serif}"
        "body{background:#1A1A2E;color:#E0E0E0;padding:25px}"
        "h1{text-align:center;margin-bottom:5px;font-size:20px}"
        "h3{color:#3498DB;font-size:14px;margin-bottom:12px}"
        ".sub{text-align:center;color:#A0A0A0;font-size:12px;margin-bottom:25px}"
        ".box{background:#16213E;border-radius:10px;padding:20px;margin-bottom:18px}"
        "textarea{width:100%;background:#1A1A2E;color:#E0E0E0;border:1px solid #2D2D4E;border-radius:6px;padding:12px;font-size:13px;font-family:monospace;resize:vertical}"
        ".btn-exec{background:#3498DB;color:#fff;border:none;padding:10px 24px;border-radius:6px;cursor:pointer;font-size:13px;margin-top:10px}"
        "</style></head><body>"
        "<h1>Explorador SQL — Imprenta Offset</h1>"
        "<p class='sub'>Ultima actualizacion: " + ts + "</p>"
        "<div class='box'><h3>TABLAS DISPONIBLES</h3>" + tablas_info + "</div>"
        "<form method='POST'>"
        "<div class='box'><h3>CONSULTAS RAPIDAS</h3>" + botones + "</div>"
        "<div class='box'><h3>CONSULTA PERSONALIZADA</h3>"
        "<textarea name='sql_custom' rows='5' placeholder='Escribi tu consulta SQL aqui...'>" + sql_actual + "</textarea>"
        "<br><button type='submit' class='btn-exec'>Ejecutar consulta</button>"
        "</div></form>" + res_block + error_html + "</body></html>")

if __name__ == "__main__":
    print("Explorador SQL iniciado.")
    print("Abri tu navegador en: http://127.0.0.1:8052")
    app.run(debug=False, port=8052)
