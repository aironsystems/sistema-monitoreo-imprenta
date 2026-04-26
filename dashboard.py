import sqlite3
import json
from flask import Flask
from datetime import datetime

app = Flask(__name__)

def cargar_datos():
    con = sqlite3.connect('imprenta.db')
    cur = con.cursor()
    cur.execute("SELECT fecha_hora, ejemplares FROM produccion ORDER BY fecha_hora DESC LIMIT 50")
    produccion = cur.fetchall()
    cur.execute("SELECT fecha_hora, motor_principal, motor_entintado, motor_humedad, nivel_tinta, nivel_humedad, diametro_rollo FROM estados ORDER BY fecha_hora DESC LIMIT 50")
    estados = cur.fetchall()
    cur.execute("SELECT fecha_hora, tipo, descripcion FROM alarmas ORDER BY fecha_hora DESC LIMIT 10")
    alarmas = cur.fetchall()
    con.close()
    return produccion, estados, alarmas

@app.route("/")
def index():
    produccion, estados, alarmas = cargar_datos()
    ultimo = estados[0] if estados else (None, 0, 0, 0, 0, 0, 0)
    mp = ultimo[1]
    me = ultimo[2]
    mh = ultimo[3]
    di = ultimo[6]

    def cm(v):
        return "#2ECC71" if v == 1 else "#E74C3C"

    def tm(v):
        return "ACTIVO" if v == 1 else "INACTIVO"

    cd = "#F39C12" if di and di < 910 else "#2ECC71"
    pl  = json.dumps([r[0][-8:] for r in reversed(produccion)])
    pd_ = json.dumps([r[1]      for r in reversed(produccion)])
    tl  = json.dumps([r[0][-8:] for r in reversed(estados)])
    td  = json.dumps([r[4]      for r in reversed(estados)])
    hd  = json.dumps([r[5]      for r in reversed(estados)])
    ts  = datetime.now().strftime("%H:%M:%S")

    filas = ""
    for a in alarmas:
        c = "#E74C3C" if a[1] == "ALERTA" else "#F39C12"
        filas += "<tr><td style='color:#A0A0A0;padding:8px'>" + a[0] + "</td><td style='color:" + c + ";padding:8px;font-weight:bold'>" + a[1] + "</td><td style='color:#E0E0E0;padding:8px'>" + a[2] + "</td></tr>"
    if not filas:
        filas = "<tr><td colspan='3' style='color:#A0A0A0;padding:8px'>Sin alarmas registradas.</td></tr>"

    p1 = "<div class='panel'><p>Motor Principal</p><h2 style='color:" + cm(mp) + "'>" + tm(mp) + "</h2></div>"
    p2 = "<div class='panel'><p>Motor Entintado</p><h2 style='color:" + cm(me) + "'>" + tm(me) + "</h2></div>"
    p3 = "<div class='panel'><p>Motor Humedad</p><h2 style='color:"  + cm(mh) + "'>" + tm(mh) + "</h2></div>"
    p4 = "<div class='panel'><p>Diametro Rollo</p><h2 style='color:" + cd     + "'>" + str(di) + " mm</h2></div>"

    gc1 = "new Chart(document.getElementById('gp'),{type:'line',data:{labels:" + pl + ",datasets:[{label:'Ejemplares',data:" + pd_ + ",borderColor:'#3498DB',backgroundColor:'rgba(52,152,219,0.1)',tension:0.3,pointRadius:4}]},options:{plugins:{legend:{labels:{color:'#E0E0E0'}}},scales:{x:{ticks:{color:'#A0A0A0'},grid:{color:'#2D2D4E'}},y:{ticks:{color:'#A0A0A0'},grid:{color:'#2D2D4E'}}}}});"
    gc2 = "new Chart(document.getElementById('gn'),{type:'line',data:{labels:" + tl + ",datasets:[{label:'Tinta %',data:" + td + ",borderColor:'#E74C3C',backgroundColor:'rgba(231,76,60,0.1)',tension:0.3,pointRadius:4},{label:'Humedad %',data:" + hd + ",borderColor:'#2ECC71',backgroundColor:'rgba(46,204,113,0.1)',tension:0.3,pointRadius:4}]},options:{plugins:{legend:{labels:{color:'#E0E0E0'}}},scales:{x:{ticks:{color:'#A0A0A0'},grid:{color:'#2D2D4E'}},y:{min:70,max:100,ticks:{color:'#A0A0A0'},grid:{color:'#2D2D4E'}}}}});"

    return (
        "<!DOCTYPE html><html><head><meta charset='UTF-8'>"
        "<meta http-equiv='refresh' content='5'>"
        "<title>Monitor Imprenta</title>"
        "<script src='https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js'></script>"
        "<style>"
        "*{margin:0;padding:0;box-sizing:border-box;font-family:Arial,sans-serif}"
        "body{background:#1A1A2E;color:#E0E0E0;padding:20px}"
        "h1{text-align:center;margin-bottom:25px;font-size:22px}"
        "h3{color:#A0A0A0;font-size:13px;margin-bottom:12px}"
        ".row{display:flex;gap:15px;margin-bottom:20px}"
        ".panel{flex:1;background:#16213E;border-radius:10px;padding:20px;text-align:center}"
        ".panel p{color:#A0A0A0;font-size:13px;margin-bottom:8px}"
        ".panel h2{font-size:20px}"
        ".box{flex:1;background:#16213E;border-radius:10px;padding:20px}"
        "table{width:100%;border-collapse:collapse}"
        ".ts{text-align:center;color:#555;font-size:12px;margin-top:15px}"
        "</style></head><body>"
        "<h1>Sistema de Monitoreo - Imprenta Offset</h1>"
        "<div class='row'>" + p1 + p2 + p3 + p4 + "</div>"
        "<div class='row'>"
        "<div class='box'><h3>PRODUCCION POR CICLO</h3><canvas id='gp'></canvas></div>"
        "<div class='box'><h3>TINTA Y HUMEDAD</h3><canvas id='gn'></canvas></div>"
        "</div>"
        "<div class='box'><h3>ULTIMAS ALARMAS</h3><table>" + filas + "</table></div>"
        "<p class='ts'>Ultima actualizacion: " + ts + " - Recarga automatica cada 5 segundos</p>"
        "<script>" + gc1 + gc2 + "</script>"
        "</body></html>"
    )

if __name__ == "__main__":
    print("Dashboard iniciado.")
    print("Abri tu navegador en: http://127.0.0.1:8050")
    app.run(debug=False, port=8050)
