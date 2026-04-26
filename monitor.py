import sqlite3
import time
import random
from datetime import datetime

# ── Configuración ─────────────────────────────────────────────────────────────
INTERVALO_SEGUNDOS = 5
DURACION_PRUEBA    = 120
RPM_NOMINAL        = 1200.0
EJEMPLARES_NOMINAL = 150
DIAMETRO_INICIAL   = 960.0
DIAMETRO_CAMBIO    = 900.0
DIAMETRO_MINIMO    = 860.0

# ── Estado global del sistema ─────────────────────────────────────────────────
estado_sistema = {
    "rollo_activo":      1,
    "diametro_rollo_1":  DIAMETRO_INICIAL,
    "diametro_rollo_2":  DIAMETRO_INICIAL,
}

def conectar():
    return sqlite3.connect('imprenta.db')

# ── Simulación de desgaste de rollo ──────────────────────────────────────────
def actualizar_rollos():
    desgaste = round(random.uniform(3.0, 7.0), 1)

    if estado_sistema["rollo_activo"] == 1:
        estado_sistema["diametro_rollo_1"] -= desgaste
        activo   = estado_sistema["diametro_rollo_1"]
        reserva  = estado_sistema["diametro_rollo_2"]
    else:
        estado_sistema["diametro_rollo_2"] -= desgaste
        activo   = estado_sistema["diametro_rollo_2"]
        reserva  = estado_sistema["diametro_rollo_1"]

    return round(activo, 1), round(reserva, 1)

# ── Lógica de cambio automático de rollo ─────────────────────────────────────
def verificar_cambio_rollo(diametro_activo):
    evento_cambio = False

    if diametro_activo <= DIAMETRO_CAMBIO:
        rollo_anterior = estado_sistema["rollo_activo"]

        if estado_sistema["rollo_activo"] == 1:
            estado_sistema["rollo_activo"]     = 2
            estado_sistema["diametro_rollo_1"] = DIAMETRO_INICIAL
        else:
            estado_sistema["rollo_activo"]     = 1
            estado_sistema["diametro_rollo_2"] = DIAMETRO_INICIAL

        evento_cambio = True
        print(f"  [CAMBIO] Rollo {rollo_anterior} agotado. Activando rollo {estado_sistema['rollo_activo']}. Rollo anterior repuesto.")

    return evento_cambio

# ── Simulación de sensores ────────────────────────────────────────────────────
def leer_sensores(diametro_activo):
    evento = random.random()
    if evento < 0.1:
        rpm = round(random.uniform(900.0, 1050.0), 1)
    else:
        rpm = round(random.uniform(1180.0, 1220.0), 1)

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

# ── Cálculo de eficiencia ─────────────────────────────────────────────────────
def calcular_eficiencia(datos):
    return round((datos["velocidad_rpm"] / RPM_NOMINAL) * 100, 1)

# ── Detección de alarmas ──────────────────────────────────────────────────────
def verificar_alarmas(datos, eficiencia, evento_cambio):
    alarmas = []

    if evento_cambio:
        alarmas.append(("INFO", f"Cambio automatico al rollo {estado_sistema['rollo_activo']} ejecutado correctamente"))

    if eficiencia < 90.0:
        alarmas.append(("ALERTA", f"Eficiencia de linea baja: {eficiencia}%"))

    if datos["nivel_tinta"] < 82.0:
        alarmas.append(("ALERTA", "Nivel de tinta bajo del umbral recomendado"))

    if datos["nivel_humedad"] < 87.0:
        alarmas.append(("ALERTA", "Nivel de humedad bajo del umbral recomendado"))

    if datos["velocidad_rpm"] < 1100.0:
        alarmas.append(("CRITICO", f"Velocidad critica detectada: {datos['velocidad_rpm']} RPM"))

    if datos["diametro_rollo"] < DIAMETRO_MINIMO:
        alarmas.append(("CRITICO", "Rollo activo en diametro minimo critico"))

    return alarmas

# ── Guardado ──────────────────────────────────────────────────────────────────
def guardar_registro(datos, eficiencia, alarmas, diametro_reserva):
    con   = conectar()
    cur   = con.cursor()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    estado = "critico" if any(a[0] == "CRITICO" for a in alarmas) else "alarma" if alarmas else "operando"

    cur.execute(
        "INSERT INTO produccion (fecha_hora, ejemplares, velocidad_rpm, estado_linea, eficiencia) VALUES (?, ?, ?, ?, ?)",
        (ahora, datos["ejemplares"], datos["velocidad_rpm"], estado, eficiencia)
    )
    cur.execute(
        "INSERT INTO estados (fecha_hora, motor_principal, motor_entintado, motor_humedad, nivel_tinta, nivel_humedad, diametro_rollo, rollo_activo, diametro_reserva) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (ahora, datos["motor_principal"], datos["motor_entintado"], datos["motor_humedad"],
         datos["nivel_tinta"], datos["nivel_humedad"], datos["diametro_rollo"],
         estado_sistema["rollo_activo"], diametro_reserva)
    )
    for tipo, descripcion in alarmas:
        cur.execute(
            "INSERT INTO alarmas (fecha_hora, tipo, descripcion, resuelta) VALUES (?, ?, ?, ?)",
            (ahora, tipo, descripcion, 0)
        )

    con.commit()
    con.close()

# ── Bucle principal ───────────────────────────────────────────────────────────
def main():
    print("Monitor iniciado con sistema de cambio de rollo.")
    print(f"Umbral de cambio: {DIAMETRO_CAMBIO} mm | Diametro inicial: {DIAMETRO_INICIAL} mm")
    print("-" * 70)

    inicio = time.time()
    ciclo  = 1

    while time.time() - inicio < DURACION_PRUEBA:
        diametro_activo, diametro_reserva = actualizar_rollos()
        evento_cambio                      = verificar_cambio_rollo(diametro_activo)

        if evento_cambio:
            diametro_activo, diametro_reserva = actualizar_rollos()

        datos      = leer_sensores(diametro_activo)
        eficiencia = calcular_eficiencia(datos)
        alarmas    = verificar_alarmas(datos, eficiencia, evento_cambio)
        estado_txt = "CRITICO" if any(a[0] == "CRITICO" for a in alarmas) else "CAMBIO" if evento_cambio else "ALARMA" if alarmas else "OK"

        print(
            f"Ciclo {ciclo:02d} | {datetime.now().strftime('%H:%M:%S')} | "
            f"Rollo {estado_sistema['rollo_activo']} | "
            f"Diam: {diametro_activo:6.1f} mm | "
            f"Efic: {eficiencia:5.1f}% | "
            f"Estado: {estado_txt}"
        )

        for tipo, desc in alarmas:
            print(f"  [{tipo}] {desc}")

        guardar_registro(datos, eficiencia, alarmas, diametro_reserva)

        ciclo += 1
        time.sleep(INTERVALO_SEGUNDOS)

    print("-" * 70)
    print(f"Prueba finalizada. {ciclo - 1} ciclos registrados.")

if __name__ == "__main__":
    main()