import sqlite3
from datetime import datetime

def conectar():
    return sqlite3.connect('imprenta.db')

def calcular_tendencia():
    con = conectar()
    cur = con.cursor()

    # Traer todos los registros de produccion ordenados por fecha
    cur.execute('''
        SELECT fecha_hora, ejemplares, eficiencia, velocidad_rpm, estado_linea
        FROM produccion
        WHERE eficiencia IS NOT NULL
        ORDER BY fecha_hora ASC
    ''')
    registros = cur.fetchall()
    con.close()

    if len(registros) < 4:
        print("No hay suficientes registros para calcular tendencia.")
        print("Corré monitor.py al menos 60 segundos y volvé a intentar.")
        return

    # Dividir registros en dos mitades para comparar
    mitad      = len(registros) // 2
    primera    = registros[:mitad]
    segunda    = registros[mitad:]

    # Calcular métricas de cada mitad
    def metricas(grupo):
        eficiencias  = [r[2] for r in grupo if r[2] is not None]
        ejemplares   = [r[1] for r in grupo]
        velocidades  = [r[3] for r in grupo]
        criticos     = sum(1 for r in grupo if r[4] == "critico")
        return {
            "eficiencia_prom": round(sum(eficiencias) / len(eficiencias), 1) if eficiencias else 0,
            "ejemplares_tot":  sum(ejemplares),
            "velocidad_prom":  round(sum(velocidades) / len(velocidades), 1),
            "eventos_criticos": criticos,
            "ciclos":          len(grupo),
            "inicio":          grupo[0][0],
            "fin":             grupo[-1][0],
        }

    m1 = metricas(primera)
    m2 = metricas(segunda)

    # Calcular variaciones
    var_eficiencia  = round(m2["eficiencia_prom"]  - m1["eficiencia_prom"],  1)
    var_velocidad   = round(m2["velocidad_prom"]   - m1["velocidad_prom"],   1)
    var_ejemplares  = m2["ejemplares_tot"] - m1["ejemplares_tot"]

    def flecha(valor):
        if valor > 0:
            return "SUBIO"
        elif valor < 0:
            return "BAJO"
        return "ESTABLE"

    def color_tendencia(valor, invertido=False):
        if invertido:
            return "MEJORA" if valor < 0 else "EMPEORA" if valor > 0 else "ESTABLE"
        return "MEJORA" if valor > 0 else "EMPEORA" if valor < 0 else "ESTABLE"

    # Determinar tendencia general
    if var_eficiencia >= 2:
        tendencia_general = "MEJORANDO"
        conclusion = "La linea muestra una tendencia positiva. Mantener condiciones actuales."
    elif var_eficiencia <= -2:
        tendencia_general = "EMPEORANDO"
        conclusion = "La linea muestra degradacion de rendimiento. Revisar motores y niveles."
    else:
        tendencia_general = "ESTABLE"
        conclusion = "La linea opera de manera consistente sin cambios significativos."

    # Mostrar análisis
    linea = "=" * 60
    print(linea)
    print("   ANALISIS DE TENDENCIA — IMPRENTA OFFSET")
    print(f"   Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(linea)

    print(f"\n   PERIODO ANTERIOR ({m1['ciclos']} ciclos)")
    print(f"   Desde : {m1['inicio']}")
    print(f"   Hasta : {m1['fin']}")
    print(f"   Eficiencia promedio : {m1['eficiencia_prom']}%")
    print(f"   Velocidad promedio  : {m1['velocidad_prom']} RPM")
    print(f"   Total ejemplares    : {m1['ejemplares_tot']:,}")
    print(f"   Eventos criticos    : {m1['eventos_criticos']}")

    print(f"\n   PERIODO ACTUAL ({m2['ciclos']} ciclos)")
    print(f"   Desde : {m2['inicio']}")
    print(f"   Hasta : {m2['fin']}")
    print(f"   Eficiencia promedio : {m2['eficiencia_prom']}%")
    print(f"   Velocidad promedio  : {m2['velocidad_prom']} RPM")
    print(f"   Total ejemplares    : {m2['ejemplares_tot']:,}")
    print(f"   Eventos criticos    : {m2['eventos_criticos']}")

    print(f"\n   VARIACIONES")
    print(f"   Eficiencia  : {'+' if var_eficiencia > 0 else ''}{var_eficiencia}% — {flecha(var_eficiencia)} ({color_tendencia(var_eficiencia)})")
    print(f"   Velocidad   : {'+' if var_velocidad > 0 else ''}{var_velocidad} RPM — {flecha(var_velocidad)} ({color_tendencia(var_velocidad)})")
    print(f"   Ejemplares  : {'+' if var_ejemplares > 0 else ''}{var_ejemplares:,} — {flecha(var_ejemplares)} ({color_tendencia(var_ejemplares)})")
    print(f"   Crit. prev  : {m1['eventos_criticos']} | Crit. actual: {m2['eventos_criticos']} — {color_tendencia(m2['eventos_criticos'] - m1['eventos_criticos'], invertido=True)}")

    print(linea)
    print(f"   TENDENCIA GENERAL: {tendencia_general}")
    print(f"   {conclusion}")
    print(linea)

    # Guardar análisis en base de datos
    con = conectar()
    cur = con.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tendencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT,
            eficiencia_anterior REAL,
            eficiencia_actual REAL,
            variacion_eficiencia REAL,
            tendencia_general TEXT,
            conclusion TEXT
        )
    ''')
    cur.execute('''
        INSERT INTO tendencias (
            fecha_hora, eficiencia_anterior, eficiencia_actual,
            variacion_eficiencia, tendencia_general, conclusion
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        m1["eficiencia_prom"], m2["eficiencia_prom"],
        var_eficiencia, tendencia_general, conclusion
    ))
    con.commit()
    con.close()
    print("   Analisis guardado en la base de datos.")
    print(linea)

if __name__ == "__main__":
    calcular_tendencia()