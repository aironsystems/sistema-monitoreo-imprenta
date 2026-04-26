import sqlite3
from datetime import datetime

def conectar():
    return sqlite3.connect('imprenta.db', check_same_thread=False)

def calcular_mtbf_mttr():
    con = conectar()
    cur = con.cursor()

    # Traer todas las fallas resueltas con duración
    cur.execute('''
        SELECT fecha_inicio, fecha_fin, duracion_segundos
        FROM fallas
        WHERE resuelta = 1 AND duracion_segundos IS NOT NULL
        ORDER BY fecha_inicio ASC
    ''')
    fallas = cur.fetchall()

    # Traer tiempo total de operación
    cur.execute("SELECT MIN(fecha_hora), MAX(fecha_hora) FROM produccion")
    rango = cur.fetchone()

    # Totales de producción
    cur.execute("SELECT COUNT(*), SUM(ejemplares) FROM produccion")
    totales = cur.fetchone()

    # Eficiencia promedio global
    cur.execute("SELECT AVG(eficiencia) FROM produccion WHERE eficiencia IS NOT NULL")
    eficiencia_global = cur.fetchone()[0]

    con.close()

    resultado = {
        "mtbf":              None,
        "mttr":              None,
        "disponibilidad":    None,
        "total_fallas":      len(fallas),
        "total_ciclos":      totales[0] if totales[0] else 0,
        "total_ejemplares":  totales[1] if totales[1] else 0,
        "eficiencia_global": round(eficiencia_global, 1) if eficiencia_global else 0,
        "primera_lectura":   rango[0] if rango else None,
        "ultima_lectura":    rango[1] if rango else None,
    }

    if len(fallas) >= 1:
        # MTTR: promedio de tiempo de reparación
        duraciones = [f[2] for f in fallas if f[2] is not None]
        mttr = sum(duraciones) / len(duraciones) if duraciones else 0

        # MTBF: tiempo total operando dividido cantidad de fallas
        if rango[0] and rango[1]:
            fmt = "%Y-%m-%d %H:%M:%S"
            inicio = datetime.strptime(rango[0], fmt)
            fin    = datetime.strptime(rango[1], fmt)
            tiempo_total = (fin - inicio).total_seconds()
            tiempo_fallas = sum(duraciones)
            tiempo_operando = tiempo_total - tiempo_fallas
            mtbf = tiempo_operando / len(fallas) if len(fallas) > 0 else tiempo_operando

            # Disponibilidad: porcentaje del tiempo que la máquina estuvo operando
            disponibilidad = round((tiempo_operando / tiempo_total) * 100, 1) if tiempo_total > 0 else 100.0

            resultado["mtbf"]           = round(mtbf, 1)
            resultado["mttr"]           = round(mttr, 1)
            resultado["disponibilidad"] = disponibilidad

    return resultado

def imprimir_indicadores():
    ind   = calcular_mtbf_mttr()
    linea = "=" * 60

    print(linea)
    print("   INDICADORES DE CONFIABILIDAD — IMPRENTA OFFSET")
    print(f"   Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(linea)
    print(f"   Total de ciclos registrados : {ind['total_ciclos']}")
    print(f"   Total de ejemplares         : {ind['total_ejemplares']:,}")
    print(f"   Eficiencia global promedio  : {ind['eficiencia_global']}%")
    print(f"   Total de fallas registradas : {ind['total_fallas']}")
    print(linea)

    if ind["mtbf"] is not None:
        print(f"   MTBF (tiempo entre fallas)  : {ind['mtbf']:.0f} segundos")
        print(f"   MTTR (tiempo de reparacion) : {ind['mttr']:.0f} segundos")
        print(f"   Disponibilidad de la linea  : {ind['disponibilidad']}%")
        print(linea)

        if ind["disponibilidad"] >= 95:
            eval_disp = "EXCELENTE — Linea con alta confiabilidad."
        elif ind["disponibilidad"] >= 85:
            eval_disp = "BUENA — Dentro del rango aceptable industrial."
        elif ind["disponibilidad"] >= 70:
            eval_disp = "REGULAR — Revisar causas de parada frecuente."
        else:
            eval_disp = "CRITICA — Mantenimiento urgente requerido."

        print(f"   Evaluacion: {eval_disp}")
    else:
        print("   Sin suficientes fallas registradas para calcular MTBF/MTTR.")
        print("   Ejecuta sistema.py varias veces para acumular datos.")

    print(linea)

if __name__ == "__main__":
    imprimir_indicadores()