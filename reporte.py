import sqlite3
from datetime import datetime

def conectar():
    return sqlite3.connect('imprenta.db')

def generar_reporte(minutos=2):
    con = conectar()
    cur = con.cursor()

    # Traer registros del período
    cur.execute('''
        SELECT ejemplares, eficiencia, estado_linea
        FROM produccion
        ORDER BY fecha_hora DESC
        LIMIT ?
    ''', (int(minutos * 60 / 5),))
    registros = cur.fetchall()

    cur.execute('''
        SELECT tipo, COUNT(*) as cantidad
        FROM alarmas
        GROUP BY tipo
        ORDER BY tipo
    ''')
    alarmas_agrupadas = cur.fetchall()

    cur.execute('''
        SELECT COUNT(*) FROM alarmas
        WHERE tipo = "INFO"
        AND descripcion LIKE "%Cambio automatico%"
    ''')
    cambios_rollo = cur.fetchone()[0]

    con.close()

    if not registros:
        print("No hay registros suficientes para generar un reporte.")
        return

    # Calcular métricas
    total_ejemplares   = sum(r[0] for r in registros)
    eficiencias        = [r[1] for r in registros if r[1] is not None]
    eficiencia_promedio = round(sum(eficiencias) / len(eficiencias), 1) if eficiencias else 0

    conteo_alarmas = {"INFO": 0, "AVISO": 0, "ALERTA": 0, "CRITICO": 0}
    for tipo, cantidad in alarmas_agrupadas:
        if tipo in conteo_alarmas:
            conteo_alarmas[tipo] = cantidad

    # Mostrar reporte en pantalla
    linea = "=" * 55
    print(linea)
    print("   REPORTE DE TURNO — IMPRENTA OFFSET")
    print(f"   Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(linea)
    print(f"   Duracion analizada  : {minutos} minutos")
    print(f"   Total ejemplares    : {total_ejemplares:,}")
    print(f"   Eficiencia promedio : {eficiencia_promedio}%")
    print(f"   Cambios de rollo    : {cambios_rollo}")
    print(linea)
    print("   ALARMAS REGISTRADAS")
    print(f"   INFO    : {conteo_alarmas['INFO']}")
    print(f"   AVISO   : {conteo_alarmas['AVISO']}")
    print(f"   ALERTA  : {conteo_alarmas['ALERTA']}")
    print(f"   CRITICO : {conteo_alarmas['CRITICO']}")
    print(linea)

    # Evaluación automática de la eficiencia
    if eficiencia_promedio >= 95:
        evaluacion = "EXCELENTE — Linea operando en condiciones optimas."
    elif eficiencia_promedio >= 90:
        evaluacion = "BUENA — Linea dentro del rango aceptable."
    elif eficiencia_promedio >= 80:
        evaluacion = "REGULAR — Revisar causas de perdida de velocidad."
    else:
        evaluacion = "CRITICA — Linea requiere intervencion inmediata."

    print(f"   Evaluacion: {evaluacion}")
    print(linea)

    # Guardar reporte en la base de datos
    con = conectar()
    cur = con.cursor()
    cur.execute('''
        INSERT INTO reportes (
            fecha_hora, total_ejemplares, eficiencia_promedio,
            alarmas_info, alarmas_aviso, alarmas_alerta, alarmas_critico,
            cambios_rollo, duracion_minutos
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_ejemplares, eficiencia_promedio,
        conteo_alarmas["INFO"], conteo_alarmas["AVISO"],
        conteo_alarmas["ALERTA"], conteo_alarmas["CRITICO"],
        cambios_rollo, minutos
    ))
    con.commit()
    con.close()

    print("   Reporte guardado en la base de datos.")
    print(linea)

if __name__ == "__main__":
    generar_reporte(minutos=2)