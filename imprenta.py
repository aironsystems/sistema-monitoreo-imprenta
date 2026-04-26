import sqlite3
from datetime import datetime

# ── Conexión a la base de datos ───────────────────────────────────────────────
# Si el archivo no existe, SQLite lo crea automáticamente
conexion = sqlite3.connect('imprenta.db')
cursor = conexion.cursor()

# ── Creación de tablas ────────────────────────────────────────────────────────

# Tabla 1: Producción por período
cursor.execute('''
    CREATE TABLE IF NOT EXISTS produccion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_hora TEXT,
        ejemplares INTEGER,
        velocidad_rpm REAL,
        estado_linea TEXT
    )
''')

# Tabla 2: Estado de componentes
cursor.execute('''
    CREATE TABLE IF NOT EXISTS estados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_hora TEXT,
        motor_principal INTEGER,
        motor_entintado INTEGER,
        motor_humedad INTEGER,
        nivel_tinta REAL,
        nivel_humedad REAL,
        diametro_rollo REAL
    )
''')

# Tabla 3: Alarmas y eventos
cursor.execute('''
    CREATE TABLE IF NOT EXISTS alarmas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_hora TEXT,
        tipo TEXT,
        descripcion TEXT,
        resuelta INTEGER
    )
''')

# ── Primer registro de prueba ─────────────────────────────────────────────────
# Estos valores son fijos por ahora, simulando que la máquina está operando

ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

cursor.execute('''
    INSERT INTO produccion (fecha_hora, ejemplares, velocidad_rpm, estado_linea)
    VALUES (?, ?, ?, ?)
''', (ahora, 150, 1200.0, "operando"))

cursor.execute('''
    INSERT INTO estados (fecha_hora, motor_principal, motor_entintado,
                         motor_humedad, nivel_tinta, nivel_humedad, diametro_rollo)
    VALUES (?, ?, ?, ?, ?, ?, ?)
''', (ahora, 1, 1, 1, 85.0, 90.0, 950.0))

cursor.execute('''
    INSERT INTO alarmas (fecha_hora, tipo, descripcion, resuelta)
    VALUES (?, ?, ?, ?)
''', (ahora, "INFO", "Sistema iniciado correctamente", 1))

conexion.commit()
conexion.close()

print("Base de datos creada correctamente.")
print(f"Primer registro guardado: {ahora}")
print("Abrí DB Browser y cargá el archivo imprenta.db para verificarlo.")