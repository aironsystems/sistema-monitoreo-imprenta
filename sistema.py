import sqlite3
import time
import random
import threading
from datetime import datetime
from flask import Flask
import json

# ── Importar módulos propios ──────────────────────────────────────────────────
from reporte   import generar_reporte
from tendencia import calcular_tendencia
from fallas import simular_falla, reporte_fallas
from indicadores import calcular_mtbf_mttr, imprimir_indicadores
from predictivo import analisis_predictivo
from sesiones import registrar_inicio_sesion, registrar_fin_sesion, mostrar_historial

# ── Configuración general ─────────────────────────────────────────────────────
INTERVALO_SEGUNDOS = 5
DURACION_TURNO     = 120
RPM_NOMINAL        = 1200.0
EJEMPLARES_NOMINAL = 150
DIAMETRO_INICIAL   = 960.0
DIAMETRO_CAMBIO    = 900.0
DIAMETRO_MINIMO    = 860.0

# ── Estado global ─────────────────────────────────────────────────────────────
estado_sistema = {
    "rollo_activo":     1,
    "diametro_rollo_1": DIAMETRO_INICIAL,
    "diametro_rollo_2": DIAMETRO_INICIAL,
    "corriendo":        True,
}

# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 1 — BASE DE DATOS
# ═════════════════════════════════════════════════════════════════════════════
def conectar():
    return sqlite3.connect('imprenta.db', check_same_thread=False)

def inicializar_db():
    con = conectar()
    cur = con.cursor()
    tablas = [
        '''CREATE TABLE IF NOT EXISTS produccion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT, ejemplares INTEGER,
            velocidad_rpm REAL, estado_linea TEXT, eficiencia REAL)''',
        '''CREATE TABLE IF NOT EXISTS estados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT, motor_principal INTEGER,
            motor_entintado INTEGER, motor_humedad INTEGER,
            nivel_tinta REAL, nivel_humedad REAL,
            diametro_rollo REAL, rollo_activo INTEGER,
            diametro_reserva REAL)''',
        '''CREATE TABLE IF NOT EXISTS alarmas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT, tipo TEXT,
            descripcion TEXT, resuelta INTEGER)''',
        '''CREATE TABLE IF NOT EXISTS reportes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT, total_ejemplares INTEGER,
            eficiencia_promedio REAL, alarmas_info INTEGER,
            alarmas_aviso INTEGER, alarmas_alerta INTEGER,
            alarmas_critico INTEGER, cambios_rollo INTEGER,
            duracion_minutos REAL)''',
        '''CREATE TABLE IF NOT EXISTS tendencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT, eficiencia_anterior REAL,
            eficiencia_actual REAL, variacion_eficiencia REAL,
            tendencia_general TEXT, conclusion TEXT)''',
    ]
    for sql in tablas:
        cur.execute(sql)
    columnas_extra = [
        ("produccion", "eficiencia",       "REAL"),
        ("estados",    "rollo_activo",     "INTEGER"),
        ("estados",    "diametro_reserva", "REAL"),
    ]
    for tabla, columna, tipo in columnas_extra:
        try:
            cur.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}")
        except Exception:
            pass
    con.commit()
    con.close()
    print("Base de datos inicializada correctamente.")

# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 2 — MONITOR
# ═════════════════════════════════════════════════════════════════════════════
def actualizar_rollos():
    desgaste = round(random.uniform(3.0, 7.0), 1)
    if estado_sistema["rollo_activo"] == 1:
        estado_sistema["diametro_rollo_1"] -= desgaste
        activo  = estado_sistema["diametro_rollo_1"]
        reserva = estado_sistema["diametro_rollo_2"]
    else:
        estado_sistema["diametro_rollo_2"] -= desgaste
        activo  = estado_sistema["diametro_rollo_2"]
        reserva = estado_sistema["diametro_rollo_1"]
    return round(activo, 1), round(reserva, 1)

def verificar_cambio_rollo(diametro_activo):
    if diametro_activo <= DIAMETRO_CAMBIO:
        rollo_anterior = estado_sistema["rollo_activo"]
        if estado_sistema["rollo_activo"] == 1:
            estado_sistema["rollo_activo"]     = 2
            estado_sistema["diametro_rollo_1"] = DIAMETRO_INICIAL
        else:
            estado_sistema["rollo_activo"]     = 1
            estado_sistema["diametro_rollo_2"] = DIAMETRO_INICIAL
        print(f"  [CAMBIO] Rollo {rollo_anterior} agotado. Activando rollo {estado_sistema['rollo_activo']}.")
        return True
    return False

def leer_sensores(diametro_activo):
    rpm = round(random.uniform(900.0, 1050.0) if random.random() < 0.1 else random.uniform(1180.0, 1220.0), 1)
    return {
        "ejemplares":      int(rpm * EJEMPLARES_NOMINAL / RPM_NOMINAL),
        "velocidad_rpm":   rpm,
        "motor_principal": 1,
        "motor_entintado": 1,
        "motor_humedad":   1,
        "nivel_tinta":     round(random.uniform(80.0, 92.0), 1),
        "nivel_humedad":   round(random.uniform(85.0, 95.0), 1),
        "diametro_rollo":  diametro_activo,
    }

def calcular_eficiencia(datos):
    return round((datos["velocidad_rpm"] / RPM_NOMINAL) * 100, 1)

def verificar_alarmas(datos, eficiencia, evento_cambio):
    alarmas = []
    if evento_cambio:
        alarmas.append(("INFO", f"Cambio automatico al rollo {estado_sistema['rollo_activo']} ejecutado"))
    if eficiencia < 90.0:
        alarmas.append(("ALERTA", f"Eficiencia baja: {eficiencia}%"))
    if datos["nivel_tinta"] < 82.0:
        alarmas.append(("ALERTA", "Nivel de tinta bajo del umbral"))
    if datos["nivel_humedad"] < 87.0:
        alarmas.append(("ALERTA", "Nivel de humedad bajo del umbral"))
    if datos["velocidad_rpm"] < 1100.0:
        alarmas.append(("CRITICO", f"Velocidad critica: {datos['velocidad_rpm']} RPM"))
    if datos["diametro_rollo"] < DIAMETRO_MINIMO:
        alarmas.append(("CRITICO", "Rollo activo en diametro minimo critico"))
    return alarmas

def guardar_registro(datos, eficiencia, alarmas, diametro_reserva):
    con   = conectar()
    cur   = con.cursor()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    estado = "critico" if any(a[0] == "CRITICO" for a in alarmas) else "alarma" if alarmas else "operando"
    cur.execute(
        "INSERT INTO produccion (fecha_hora, ejemplares, velocidad_rpm, estado_linea, eficiencia) VALUES (?,?,?,?,?)",
        (ahora, datos["ejemplares"], datos["velocidad_rpm"], estado, eficiencia)
    )
    cur.execute(
        "INSERT INTO estados (fecha_hora, motor_principal, motor_entintado, motor_humedad, nivel_tinta, nivel_humedad, diametro_rollo, rollo_activo, diametro_reserva) VALUES (?,?,?,?,?,?,?,?,?)",
        (ahora, datos["motor_principal"], datos["motor_entintado"], datos["motor_humedad"],
         datos["nivel_tinta"], datos["nivel_humedad"], datos["diametro_rollo"],
         estado_sistema["rollo_activo"], diametro_reserva)
    )
    for tipo, descripcion in alarmas:
        cur.execute(
            "INSERT INTO alarmas (fecha_hora, tipo, descripcion, resuelta) VALUES (?,?,?,?)",
            (ahora, tipo, descripcion, 0)
        )
    con.commit()
    con.close()

def correr_monitor():
    print(f"Monitor iniciado. Duracion: {DURACION_TURNO} segundos.")
    sesion_id = registrar_inicio_sesion()
    ciclos_sesion = 0
    print("-" * 65)
    inicio = time.time()
    ciclo  = 1
    while time.time() - inicio < DURACION_TURNO:
        diametro_activo, diametro_reserva = actualizar_rollos()
        evento_cambio = verificar_cambio_rollo(diametro_activo)
        if evento_cambio:
            diametro_activo, diametro_reserva = actualizar_rollos()
        datos = leer_sensores(diametro_activo)

        # Falla aleatoria con probabilidad del 8% por ciclo
        if random.random() < 0.08:
            datos = simular_falla(datos)

        eficiencia = calcular_eficiencia(datos)
        alarmas    = verificar_alarmas(datos, eficiencia, evento_cambio)
        estado_txt = "CRITICO" if any(a[0]=="CRITICO" for a in alarmas) else "CAMBIO" if evento_cambio else "ALARMA" if alarmas else "OK"
        print(
            f"Ciclo {ciclo:02d} | {datetime.now().strftime('%H:%M:%S')} | "
            f"Rollo {estado_sistema['rollo_activo']} | "
            f"Diam: {diametro_activo:6.1f} mm | "
            f"Efic: {eficiencia:5.1f}% | {estado_txt}"
        )
        for tipo, desc in alarmas:
            print(f"  [{tipo}] {desc}")
        guardar_registro(datos, eficiencia, alarmas, diametro_reserva)
        ciclo += 1
        ciclos_sesion += 1
        time.sleep(INTERVALO_SEGUNDOS)
    print("-" * 65)
    print("Monitor finalizado. Generando reporte y tendencia...")
    estado_sistema["corriendo"] = False
    resumen = registrar_fin_sesion(sesion_id, ciclos_sesion)
    print(f"\n   Sesion registrada: {resumen}")
    generar_reporte(minutos=int(DURACION_TURNO / 60))
    calcular_tendencia()
    reporte_fallas()
    analisis_predictivo()
    imprimir_indicadores()
    mostrar_historial()

# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 3 — DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════
app = Flask(__name__)

def cargar_datos_dashboard():
    con = conectar()
    cur = con.cursor()
    cur.execute("SELECT fecha_hora, ejemplares FROM produccion ORDER BY fecha_hora DESC LIMIT 50")
    produccion = cur.fetchall()
    cur.execute("SELECT fecha_hora, motor_principal, motor_entintado, motor_humedad, nivel_tinta, nivel_humedad, diametro_rollo FROM estados ORDER BY fecha_hora DESC LIMIT 50")
    estados = cur.fetchall()
    cur.execute("SELECT fecha_hora, tipo, descripcion FROM alarmas ORDER BY fecha_hora DESC LIMIT 10")
    alarmas = cur.fetchall()
    con.close()
    indicadores = calcular_mtbf_mttr()
    return produccion, estados, alarmas, indicadores

@app.route("/")
def index():
    produccion, estados, alarmas, ind = cargar_datos_dashboard()
    ultimo = estados[0] if estados else (None,0,0,0,0,0,0)
    mp = ultimo[1]; me = ultimo[2]; mh = ultimo[3]; di = ultimo[6]
    def cm(v): return "#2ECC71" if v==1 else "#E74C3C"
    def tm(v): return "ACTIVO" if v==1 else "INACTIVO"
    cd = "#F39C12" if di and di<910 else "#2ECC71"
    pl  = json.dumps([r[0][-8:] for r in reversed(produccion)])
    pd_ = json.dumps([r[1]      for r in reversed(produccion)])
    tl  = json.dumps([r[0][-8:] for r in reversed(estados)])
    td  = json.dumps([r[4]      for r in reversed(estados)])
    hd  = json.dumps([r[5]      for r in reversed(estados)])
    ts  = datetime.now().strftime("%H:%M:%S")
    estado_txt = "DETENIDO" if not estado_sistema["corriendo"] else "EN PRODUCCION"
    color_estado = "#E74C3C" if not estado_sistema["corriendo"] else "#2ECC71"
    mtbf_txt  = f"{ind['mtbf']:.0f} seg"        if ind["mtbf"]           else "Sin datos"
    mttr_txt  = f"{ind['mttr']:.0f} seg"         if ind["mttr"]           else "Sin datos"
    disp_txt  = f"{ind['disponibilidad']}%"       if ind["disponibilidad"] else "Sin datos"
    efic_txt  = f"{ind['eficiencia_global']}%"
    fallas_txt= str(ind["total_fallas"])
    ej_txt    = f"{ind['total_ejemplares']:,}"

    color_disp = "#2ECC71" if ind["disponibilidad"] and ind["disponibilidad"] >= 85 else "#E74C3C" if ind["disponibilidad"] else "#A0A0A0"
    filas = ""
    for a in alarmas:
        c = "#E74C3C" if a[1]=="ALERTA" else "#F39C12" if a[1]=="AVISO" else "#E74C3C" if a[1]=="CRITICO" else "#3498DB"
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
        "h1{text-align:center;margin-bottom:8px;font-size:22px}"
        ".subtitulo{text-align:center;margin-bottom:20px;font-size:14px}"
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
        "<p class='subtitulo'>Estado de linea: <strong style='color:" + color_estado + "'>" + estado_txt + "</strong></p>"
        "<div class='row'>"
        "<div class='panel'><p>MTBF</p><h2 style='color:#3498DB'>" + mtbf_txt + "</h2></div>"
        "<div class='panel'><p>MTTR</p><h2 style='color:#F39C12'>" + mttr_txt + "</h2></div>"
        "<div class='panel'><p>Disponibilidad</p><h2 style='color:" + color_disp + "'>" + disp_txt + "</h2></div>"
        "<div class='panel'><p>Efic. Global</p><h2 style='color:#2ECC71'>" + efic_txt + "</h2></div>"
        "<div class='panel'><p>Fallas</p><h2 style='color:#E74C3C'>" + fallas_txt + "</h2></div>"
        "<div class='panel'><p>Ejemplares</p><h2 style='color:#E0E0E0'>" + ej_txt + "</h2></div>"
        "</div>"
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

def correr_dashboard():
    print("Dashboard disponible en: http://127.0.0.1:8050")
    app.run(debug=False, port=8050, use_reloader=False)

# ═════════════════════════════════════════════════════════════════════════════
# INICIO DEL SISTEMA
# ═════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 65)
    print("   SISTEMA DE MONITOREO — IMPRENTA OFFSET")
    print("=" * 65)

    inicializar_db()

    hilo_dashboard = threading.Thread(target=correr_dashboard, daemon=True)
    hilo_dashboard.start()

    time.sleep(1)
    correr_monitor()

    print("=" * 65)
    print("   Sistema finalizado correctamente.")
    print("=" * 65)