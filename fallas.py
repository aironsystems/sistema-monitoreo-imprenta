import sqlite3
import random
import time
from datetime import datetime

def conectar():
    return sqlite3.connect('imprenta.db', check_same_thread=False)

# ── Tipos de falla posibles ───────────────────────────────────────────────────
FALLAS_POSIBLES = [
    {
        "tipo":       "MECANICA",
        "componente": "Motor Principal",
        "descripcion":"Sobrecalentamiento detectado en motor principal. Parada de emergencia.",
        "duracion":   random.randint(15, 40),
        "impacto":    {"motor_principal": 0, "velocidad_rpm": 0.0},
    },
    {
        "tipo":       "ELECTRICA",
        "componente": "Motor Entintado",
        "descripcion":"Falla electrica en motor de entintado. Sistema de tinta detenido.",
        "duracion":   random.randint(10, 25),
        "impacto":    {"motor_entintado": 0, "nivel_tinta": 0.0},
    },
    {
        "tipo":       "PROCESO",
        "componente": "Sistema de Humedad",
        "descripcion":"Nivel critico de solucion de humedad. Motor detenido por seguridad.",
        "duracion":   random.randint(8, 20),
        "impacto":    {"motor_humedad": 0, "nivel_humedad": 0.0},
    },
    {
        "tipo":       "MECANICA",
        "componente": "Rollo de Papel",
        "descripcion":"Rotura de papel detectada. Linea detenida para empalme manual.",
        "duracion":   random.randint(20, 45),
        "impacto":    {"velocidad_rpm": 0.0, "motor_principal": 0},
    },
]

# ── Registrar inicio de falla ─────────────────────────────────────────────────
def registrar_falla_inicio(falla):
    con   = conectar()
    cur   = con.cursor()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute('''
        INSERT INTO fallas (fecha_inicio, tipo_falla, componente, descripcion, resuelta)
        VALUES (?, ?, ?, ?, ?)
    ''', (ahora, falla["tipo"], falla["componente"], falla["descripcion"], 0))
    falla_id = cur.lastrowid
    cur.execute(
        "INSERT INTO alarmas (fecha_hora, tipo, descripcion, resuelta) VALUES (?, ?, ?, ?)",
        (ahora, "CRITICO", f"FALLA {falla['tipo']}: {falla['descripcion']}", 0)
    )
    con.commit()
    con.close()
    return falla_id

# ── Registrar resolución de falla ─────────────────────────────────────────────
def registrar_falla_fin(falla_id, duracion_real):
    con   = conectar()
    cur   = con.cursor()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute('''
        UPDATE fallas
        SET fecha_fin = ?, duracion_segundos = ?, resuelta = 1
        WHERE id = ?
    ''', (ahora, duracion_real, falla_id))
    cur.execute(
        "INSERT INTO alarmas (fecha_hora, tipo, descripcion, resuelta) VALUES (?, ?, ?, ?)",
        (ahora, "INFO", f"Falla resuelta. Tiempo fuera de servicio: {duracion_real:.0f} segundos.", 1)
    )
    con.commit()
    con.close()

# ── Simular una falla completa ────────────────────────────────────────────────
def simular_falla(datos_actuales):
    falla = random.choice(FALLAS_POSIBLES)
    falla["duracion"] = random.randint(10, 30)

    print(f"\n{'!'*60}")
    print(f"  FALLA DETECTADA: {falla['tipo']}")
    print(f"  Componente     : {falla['componente']}")
    print(f"  Descripcion    : {falla['descripcion']}")
    print(f"  Duracion est.  : {falla['duracion']} segundos")
    print(f"{'!'*60}\n")

    falla_id   = registrar_falla_inicio(falla)
    inicio     = time.time()

    # Aplicar impacto al estado de sensores
    datos_falla = datos_actuales.copy()
    for clave, valor in falla["impacto"].items():
        if clave in datos_falla:
            datos_falla[clave] = valor

    # Esperar duración de la falla
    time.sleep(min(falla["duracion"], 15))
    duracion_real = time.time() - inicio

    # Recuperación automática
    print(f"\n{'*'*60}")
    print(f"  RECUPERACION AUTOMATICA")
    print(f"  Componente     : {falla['componente']}")
    print(f"  Tiempo fuera   : {duracion_real:.0f} segundos")
    print(f"  Estado         : LINEA REANUDANDO PRODUCCION")
    print(f"{'*'*60}\n")

    registrar_falla_fin(falla_id, duracion_real)
    return datos_falla

# ── Reporte de fallas del turno ───────────────────────────────────────────────
def reporte_fallas():
    con = conectar()
    cur = con.cursor()
    cur.execute('''
        SELECT tipo_falla, componente, descripcion,
               duracion_segundos, resuelta, fecha_inicio
        FROM fallas
        ORDER BY fecha_inicio DESC
        LIMIT 20
    ''')
    fallas = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM fallas WHERE resuelta = 1")
    resueltas = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM fallas WHERE resuelta = 0")
    pendientes = cur.fetchone()[0]
    cur.execute("SELECT AVG(duracion_segundos) FROM fallas WHERE resuelta = 1")
    promedio = cur.fetchone()[0]
    con.close()

    linea = "=" * 60
    print(linea)
    print("   REPORTE DE FALLAS — IMPRENTA OFFSET")
    print(f"   Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(linea)
    print(f"   Fallas resueltas  : {resueltas}")
    print(f"   Fallas pendientes : {pendientes}")
    print(f"   Tiempo prom. fuera: {promedio:.0f} segundos" if promedio else "   Sin datos de duracion")
    print(linea)

    if fallas:
        print("   DETALLE DE FALLAS:")
        for f in fallas:
            estado = "RESUELTA" if f[4] == 1 else "PENDIENTE"
            dur    = f"{f[3]:.0f}s" if f[3] else "En curso"
            print(f"   [{f[0]}] {f[1]} — {dur} — {estado}")
            print(f"   Inicio: {f[5]}")
            print(f"   {f[2]}")
            print()
    print(linea)

if __name__ == "__main__":
    reporte_fallas()