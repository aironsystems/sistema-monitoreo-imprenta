import sqlite3
import json
from datetime import datetime

def conectar():
    return sqlite3.connect('imprenta.db')

def inicializar_tabla_sesiones():
    con = conectar()
    cur = con.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS sesiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_inicio TEXT,
            fecha_fin TEXT,
            total_ciclos INTEGER,
            total_ejemplares INTEGER,
            eficiencia_promedio REAL,
            velocidad_promedio REAL,
            cambios_rollo INTEGER,
            fallas_detectadas INTEGER,
            alertas_criticas INTEGER,
            tendencia_eficiencia REAL,
            resumen TEXT
        )
    ''')
    con.commit()
    con.close()

def registrar_inicio_sesion():
    inicializar_tabla_sesiones()
    con = conectar()
    cur = con.cursor()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "INSERT INTO sesiones (fecha_inicio, resumen) VALUES (?, ?)",
        (ahora, "En curso")
    )
    sesion_id = cur.lastrowid
    con.commit()
    con.close()
    return sesion_id

def registrar_fin_sesion(sesion_id, ciclos_sesion):
    con = conectar()
    cur = con.cursor()

    # Traer datos de la sesión actual
    cur.execute('''
        SELECT MIN(fecha_hora), MAX(fecha_hora),
               COUNT(*), SUM(ejemplares),
               AVG(eficiencia), AVG(velocidad_rpm)
        FROM produccion
        ORDER BY fecha_hora DESC
        LIMIT ?
    ''', (ciclos_sesion,))
    datos = cur.fetchone()

    cur.execute('''
        SELECT COUNT(*) FROM alarmas
        WHERE tipo = "INFO" AND descripcion LIKE "%Cambio automatico%"
        ORDER BY fecha_hora DESC
        LIMIT ?
    ''', (ciclos_sesion * 3,))
    cambios = cur.fetchone()[0]

    cur.execute('''
        SELECT COUNT(*) FROM fallas
        WHERE fecha_inicio >= (
            SELECT fecha_inicio FROM sesiones WHERE id = ?
        )
    ''', (sesion_id,))
    fallas = cur.fetchone()[0]

    cur.execute('''
        SELECT COUNT(*) FROM alarmas
        WHERE tipo = "CRITICO"
        ORDER BY fecha_hora DESC
        LIMIT ?
    ''', (ciclos_sesion * 3,))
    criticas = cur.fetchone()[0]

    # Calcular tendencia de eficiencia de la sesión
    cur.execute('''
        SELECT eficiencia FROM produccion
        WHERE eficiencia IS NOT NULL
        ORDER BY fecha_hora DESC
        LIMIT ?
    ''', (ciclos_sesion,))
    eficiencias = [r[0] for r in cur.fetchall()]

    tendencia = 0.0
    if len(eficiencias) >= 4:
        mitad = len(eficiencias) // 2
        prom_primera = sum(eficiencias[mitad:]) / len(eficiencias[mitad:])
        prom_segunda = sum(eficiencias[:mitad]) / len(eficiencias[:mitad])
        tendencia = round(prom_segunda - prom_primera, 2)

    efic_prom = round(datos[4], 1) if datos[4] else 0
    vel_prom  = round(datos[5], 1) if datos[5] else 0
    total_ej  = datos[3] if datos[3] else 0
    ahora     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if efic_prom >= 95:
        evaluacion = "EXCELENTE"
    elif efic_prom >= 90:
        evaluacion = "BUENA"
    elif efic_prom >= 80:
        evaluacion = "REGULAR"
    else:
        evaluacion = "CRITICA"

    resumen = (
        f"Sesion {evaluacion}. "
        f"Eficiencia: {efic_prom}%. "
        f"Ejemplares: {total_ej:,}. "
        f"Fallas: {fallas}. "
        f"Tendencia: {'+' if tendencia >= 0 else ''}{tendencia}%."
    )

    cur.execute('''
        UPDATE sesiones SET
            fecha_fin = ?,
            total_ciclos = ?,
            total_ejemplares = ?,
            eficiencia_promedio = ?,
            velocidad_promedio = ?,
            cambios_rollo = ?,
            fallas_detectadas = ?,
            alertas_criticas = ?,
            tendencia_eficiencia = ?,
            resumen = ?
        WHERE id = ?
    ''', (
        ahora, ciclos_sesion, total_ej,
        efic_prom, vel_prom, cambios, fallas,
        criticas, tendencia, resumen, sesion_id
    ))
    con.commit()
    con.close()

    return resumen

def mostrar_historial():
    con = conectar()
    cur = con.cursor()
    cur.execute('''
        SELECT id, fecha_inicio, fecha_fin, total_ciclos,
               total_ejemplares, eficiencia_promedio,
               fallas_detectadas, tendencia_eficiencia, resumen
        FROM sesiones
        ORDER BY fecha_inicio DESC
        LIMIT 10
    ''')
    sesiones = cur.fetchall()
    con.close()

    linea = "=" * 70
    print(linea)
    print("   HISTORIAL DE SESIONES — IMPRENTA OFFSET")
    print(f"   Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(linea)

    if not sesiones:
        print("   Sin sesiones registradas todavia.")
        print("   Ejecuta sistema.py para registrar la primera sesion.")
    else:
        for s in sesiones:
            print(f"\n   SESION #{s[0]}")
            print(f"   Inicio   : {s[1]}")
            print(f"   Fin      : {s[2] or 'En curso'}")
            print(f"   Ciclos   : {s[3] or 0}")
            print(f"   Ejemplares: {s[4]:,}" if s[4] else "   Ejemplares: 0")
            print(f"   Eficiencia: {s[5]}%" if s[5] else "   Eficiencia: --")
            print(f"   Fallas   : {s[6] or 0}")
            tend = s[7]
            if tend is not None:
                tend_txt = f"+{tend}% MEJORO" if tend > 0 else f"{tend}% EMPEORO" if tend < 0 else "ESTABLE"
                print(f"   Tendencia: {tend_txt}")
            print(f"   Resumen  : {s[8]}")
            print(f"   {'-'*60}")

    print(linea)

if __name__ == "__main__":
    mostrar_historial()