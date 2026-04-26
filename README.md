# Sistema de Monitoreo Industrial - Imprenta Offset

Sistema de monitoreo en tiempo real desarrollado en Python para una imprenta offset industrial.

## Funcionalidades

- Monitor de produccion en tiempo real con deteccion de alarmas
- Dashboard interactivo con graficos Plotly
- Base de datos SQLite con historial completo de produccion
- Calculo automatico de MTBF, MTTR y disponibilidad
- Deteccion de fallas y recuperacion automatica
- Analisis predictivo por regresion lineal y deteccion de anomalias
- Exportacion de datos a CSV y reportes HTML
- Explorador SQL interactivo desde el navegador
- Registro historico de sesiones

## Tecnologias

- Python 3.12
- Flask
- Plotly
- pandas
- numpy
- SQLite

## Estructura del proyecto

- sistema.py - Sistema principal unificado
- monitor.py - Monitor de produccion
- dashboard_plotly.py - Dashboard con Plotly
- consultas.py - Explorador SQL interactivo
- predictivo.py - Analisis predictivo
- exportar.py - Exportacion de datos
- sesiones.py - Historial de sesiones
- fallas.py - Simulacion y registro de fallas
- indicadores.py - Calculo de MTBF y MTTR
- reporte.py - Reportes de turno
- tendencia.py - Analisis de tendencia

## Contexto

Proyecto desarrollado como parte de mi formacion en automatizacion industrial
y analisis de datos, orientado a la Industria 4.0.
