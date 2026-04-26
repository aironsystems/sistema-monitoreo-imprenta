# Sistema de Monitoreo Industrial - Imprenta Offset

Sistema SCADA básico desarrollado en Python para el monitoreo en tiempo real
de una imprenta offset industrial. Registra producción, detecta fallas,
calcula indicadores de mantenimiento y genera reportes automáticos.

Desarrollado por Airon, técnico en automatización y estudiante de
Ingeniería en Sistemas. Proyecto orientado a la Industria 4.0.

---

## Funcionalidades principales

- Monitor de producción en tiempo real con detección de alarmas por umbral
- Dashboard interactivo con gráficos Plotly (producción, eficiencia, RPM, niveles)
- Simulación de cambio automático de rollo de papel con lógica de empalme
- Detección y registro de fallas con cálculo de tiempo fuera de servicio
- Cálculo de MTBF, MTTR y disponibilidad de línea
- Análisis predictivo por regresión lineal y detección de anomalías por sigma
- Exportación de datos a CSV y reportes HTML con gráficos interactivos
- Explorador SQL interactivo desde el navegador
- Registro histórico de sesiones con evaluación automática
- Sistema unificado: un solo comando arranca todo

---

## Tecnologías utilizadas

- Python 3.12
- Flask (servidor web liviano)
- Plotly (gráficos interactivos)
- pandas (manipulación de datos)
- numpy (cálculos numéricos y regresión lineal)
- SQLite (base de datos local)

---

## Estructura del proyecto

| Archivo | Función |
|---|---|
| sistema.py | Sistema principal unificado |
| monitor.py | Monitor de producción y sensores |
| dashboard_plotly.py | Dashboard interactivo con Plotly |
| consultas.py | Explorador SQL desde el navegador |
| predictivo.py | Análisis predictivo de variables |
| exportar.py | Exportación CSV y reportes HTML |
| sesiones.py | Historial y registro de sesiones |
| fallas.py | Simulación y registro de fallas |
| indicadores.py | Cálculo de MTBF, MTTR y disponibilidad |
| reporte.py | Reportes de turno automáticos |
| tendencia.py | Análisis de tendencia comparativa |

---

## Como correrlo

Instalar dependencias:

pip install flask plotly pandas numpy

Correr el sistema completo:

python3 sistema.py

Abrir el dashboard en el navegador:

http://127.0.0.1:8050

Explorador SQL:

http://127.0.0.1:8052

---

## Contexto y proyección

Este es el Proyecto 1 de una serie de tres etapas:

- Proyecto 1 (actual): Imprenta offset genérica con parámetros simulados
- Proyecto 2: Escalado a producción industrial real con datos de planta
- Proyecto 3: Réplica exacta de la máquina donde trabajo, con detección
  predictiva de fallas orientada al mantenimiento preventivo

---

## Indicadores de ejemplo

Estos son valores típicos que genera el sistema en una sesión de prueba:

- Eficiencia promedio de línea: 97-99%
- MTBF: variable según frecuencia de fallas simuladas
- MTTR: 15 segundos promedio (tiempo de recuperación automática)
- Disponibilidad: mayor al 99% en condiciones normales
