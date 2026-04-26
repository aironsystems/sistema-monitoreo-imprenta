import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime

def conectar():
    return sqlite3.connect('imprenta.db')

# ── Cargar datos históricos ───────────────────────────────────────────────────
def cargar_historico(ultimos_n=50):
    con = conectar()
    produccion = pd.read_sql_query(
        f"SELECT fecha_hora, velocidad_rpm, eficiencia, estado_linea FROM produccion ORDER BY fecha_hora DESC LIMIT {ultimos_n}",
        con
    )
    estados = pd.read_sql_query(
        f"SELECT fecha_hora, nivel_tinta, nivel_humedad, diametro_rollo FROM estados ORDER BY fecha_hora DESC LIMIT {ultimos_n}",
        con
    )
    con.close()
    return produccion.iloc[::-1].reset_index(drop=True), estados.iloc[::-1].reset_index(drop=True)

# ── Análisis de tendencia por regresión lineal simple ────────────────────────
def calcular_tendencia_lineal(valores):
    if len(valores) < 3:
        return 0.0
    x = np.arange(len(valores))
    y = np.array(valores, dtype=float)
    mask = ~np.isnan(y)
    if mask.sum() < 3:
        return 0.0
    coef = np.polyfit(x[mask], y[mask], 1)
    return round(float(coef[0]), 4)

# ── Detectar degradación progresiva ──────────────────────────────────────────
def detectar_degradacion(valores, umbral_critico, nombre):
    alertas = []
    if len(valores) < 5:
        return alertas

    tendencia = calcular_tendencia_lineal(valores)
    promedio  = float(np.nanmean(valores))
    ultimo    = float(valores.iloc[-1]) if not pd.isna(valores.iloc[-1]) else promedio

    # Tendencia negativa pronunciada
    if tendencia < -0.5:
        ciclos_restantes = int((umbral_critico - ultimo) / abs(tendencia)) if tendencia != 0 else 999
        ciclos_restantes = max(0, ciclos_restantes)
        alertas.append({
            "tipo":      "PREDICTIVA",
            "severidad": "ALTA" if ciclos_restantes < 10 else "MEDIA",
            "variable":  nombre,
            "mensaje":   f"{nombre} muestra caida sostenida. Tendencia: {tendencia:.3f}/ciclo. "
                        f"Valor actual: {ultimo:.1f}. "
                        f"Alcanzaria umbral critico en aprox. {ciclos_restantes} ciclos.",
        })

    # Valor cercano al umbral crítico
    margen = abs(ultimo - umbral_critico)
    if ultimo < umbral_critico * 1.05 and ultimo > umbral_critico:
        alertas.append({
            "tipo":      "PREVENTIVA",
            "severidad": "MEDIA",
            "variable":  nombre,
            "mensaje":   f"{nombre} esta al {margen:.1f} unidades del umbral critico ({umbral_critico}). Monitorear de cerca.",
        })

    return alertas

# ── Detección de anomalías por desviación estándar ───────────────────────────
def detectar_anomalias(valores, nombre):
    alertas = []
    if len(valores) < 10:
        return alertas

    media = float(np.nanmean(valores))
    std   = float(np.nanstd(valores))
    ultimo = float(valores.iloc[-1]) if not pd.isna(valores.iloc[-1]) else media

    if std == 0:
        return alertas

    z_score = abs(ultimo - media) / std

    if z_score > 2.5:
        alertas.append({
            "tipo":      "ANOMALIA",
            "severidad": "ALTA" if z_score > 3 else "MEDIA",
            "variable":  nombre,
            "mensaje":   f"{nombre} muestra un valor anomalo. "
                        f"Actual: {ultimo:.1f} | Media historica: {media:.1f} | "
                        f"Desviacion: {z_score:.1f} sigma. Verificar componente.",
        })

    return alertas

# ── Análisis completo ─────────────────────────────────────────────────────────
def analisis_predictivo():
    produccion, estados = cargar_historico(ultimos_n=100)

    if len(produccion) < 5:
        print("Insuficientes datos para analisis predictivo.")
        print("Ejecuta sistema.py al menos dos veces y volvé a intentar.")
        return

    todas_alertas = []

    # Análisis de velocidad RPM
    todas_alertas += detectar_degradacion(
        produccion["velocidad_rpm"].dropna(), umbral_critico=1100, nombre="Velocidad RPM"
    )
    todas_alertas += detectar_anomalias(
        produccion["velocidad_rpm"].dropna(), nombre="Velocidad RPM"
    )

    # Análisis de eficiencia
    todas_alertas += detectar_degradacion(
        produccion["eficiencia"].dropna(), umbral_critico=85, nombre="Eficiencia"
    )
    todas_alertas += detectar_anomalias(
        produccion["eficiencia"].dropna(), nombre="Eficiencia"
    )

    # Análisis de nivel de tinta
    todas_alertas += detectar_degradacion(
        estados["nivel_tinta"].dropna(), umbral_critico=80, nombre="Nivel de Tinta"
    )

    # Análisis de nivel de humedad
    todas_alertas += detectar_degradacion(
        estados["nivel_humedad"].dropna(), umbral_critico=85, nombre="Nivel de Humedad"
    )

    # Análisis de diámetro de rollo
    todas_alertas += detectar_degradacion(
        estados["diametro_rollo"].dropna(), umbral_critico=900, nombre="Diametro de Rollo"
    )

    # Calcular tendencias generales
    tend_efic = calcular_tendencia_lineal(produccion["eficiencia"].dropna())
    tend_rpm  = calcular_tendencia_lineal(produccion["velocidad_rpm"].dropna())
    tend_tinta= calcular_tendencia_lineal(estados["nivel_tinta"].dropna())

    # Mostrar resultado
    linea = "=" * 65
    print(linea)
    print("   ANALISIS PREDICTIVO — IMPRENTA OFFSET")
    print(f"   Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Registros analizados: {len(produccion)} ciclos de produccion")
    print(linea)

    print("\n   TENDENCIAS GENERALES:")
    print(f"   Eficiencia  : {tend_efic:+.4f}/ciclo  {'↓ BAJANDO' if tend_efic < -0.1 else '↑ SUBIENDO' if tend_efic > 0.1 else '→ ESTABLE'}")
    print(f"   Velocidad   : {tend_rpm:+.4f}/ciclo   {'↓ BAJANDO' if tend_rpm  < -0.1 else '↑ SUBIENDO' if tend_rpm  > 0.1 else '→ ESTABLE'}")
    print(f"   Tinta       : {tend_tinta:+.4f}/ciclo  {'↓ BAJANDO' if tend_tinta< -0.1 else '↑ SUBIENDO' if tend_tinta> 0.1 else '→ ESTABLE'}")

    print(f"\n   ALERTAS DETECTADAS: {len(todas_alertas)}")
    print(linea)

    if todas_alertas:
        for i, alerta in enumerate(todas_alertas, 1):
            color_sev = "⚠" if alerta["severidad"] == "ALTA" else "→"
            print(f"\n   {color_sev} ALERTA {i} [{alerta['tipo']}] — Severidad: {alerta['severidad']}")
            print(f"   Variable : {alerta['variable']}")
            print(f"   Detalle  : {alerta['mensaje']}")
    else:
        print("\n   Sin alertas predictivas. Sistema operando dentro de parametros normales.")

    print(f"\n{linea}")

    # Guardar alertas en base de datos
    if todas_alertas:
        con = conectar()
        cur = con.cursor()
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for alerta in todas_alertas:
            cur.execute(
                "INSERT INTO alarmas (fecha_hora, tipo, descripcion, resuelta) VALUES (?, ?, ?, ?)",
                (ahora, f"PRED-{alerta['severidad']}", alerta["mensaje"], 0)
            )
        con.commit()
        con.close()
        print(f"   {len(todas_alertas)} alertas predictivas guardadas en la base de datos.")
        print(linea)

if __name__ == "__main__":
    analisis_predictivo()