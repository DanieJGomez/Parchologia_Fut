import os
import re
from contextlib import contextmanager
import mysql.connector
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from mysql.connector import IntegrityError

app = Flask(__name__)
load_dotenv()
CORS(app, resources={r"/api/*": {"origins": "*"}})

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "Parchologia"),
    "charset": "utf8mb4",
    "use_unicode": True,
}
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SEDES = [
    "administrativo 40",
    "Tecnologica Tunal",
    "Vivero",
    "Macarena",
    "Bosa Porvenir",
    "ECCI sede S",
    "Aduanilla de paiba",
    "Calle 34",
    "Sabio caldas 40",
    "Santo Domingo",
    "ECCI Cristancio Luque 19",
]

MATERIAS = [
    "Cálculo Diferencial",
    "Cálculo Integral",
    "Fisica",
    "Algebra Lineal",
    "Electromagnetismo",
    "POO",
    "Teoria de Sistemas",
    "Historia",
    "Catedra de Democracia",
    "Grupo de Trabajo",
    "Electiva",
    "Cálculo multivariado",
    "Probabilidad y estadistica",
    "Ciencias de la computación 1",
    "Programación avanzada",
    "Analisis y diseño de sistemas",
    "Economia",
    "modelos de programación",
    "ecuaciones difereciales",
    "metodos numericos",
    "ciencias de la computación 2",
    "Investigación de operaciones 1",
]

@app.get("/")
def home():
    return send_from_directory(PROJECT_ROOT, "index.html")

@app.get("/src/<path:filename>")
def frontend_asset(filename):
    return send_from_directory(os.path.join(PROJECT_ROOT, "src"), filename)
def connect():
    return mysql.connector.connect(**DB_CONFIG)
def initialize_database():
    
    # The database is created when the configured MySQL account has permission.
    config = {key: value for key, value in DB_CONFIG.items() if key != "database"}
    conn = mysql.connector.connect(**config)
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.close()
    finally:
        conn.close()
    conn = connect()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS estudiantes (
                id_estudiante INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                color VARCHAR(7) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sedes (
                id_sede INT AUTO_INCREMENT PRIMARY KEY,
                nombre_sede VARCHAR(100) NOT NULL UNIQUE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS materias (
                id_materia INT AUTO_INCREMENT PRIMARY KEY,
                nombre_materia VARCHAR(100) NOT NULL UNIQUE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS huecos (
                id_hueco INT AUTO_INCREMENT PRIMARY KEY,
                id_estudiante INT NOT NULL,
                id_sede INT NOT NULL,
                id_materia INT NOT NULL,
                dia VARCHAR(15) NOT NULL,
                hora_inicio TIME NOT NULL,
                hora_fin TIME NOT NULL,
                FOREIGN KEY (id_estudiante) REFERENCES estudiantes(id_estudiante) ON DELETE CASCADE,
                FOREIGN KEY (id_sede) REFERENCES sedes(id_sede) ON DELETE CASCADE,
                FOREIGN KEY (id_materia) REFERENCES materias(id_materia) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        cursor.executemany(
            "INSERT IGNORE INTO sedes (nombre_sede) VALUES (%s)",
            [(sede,) for sede in SEDES],
        )
        cursor.executemany(
            "INSERT IGNORE INTO materias (nombre_materia) VALUES (%s)",
            [(materia,) for materia in MATERIAS],
        )
        conn.commit()
        cursor.close()
    finally:
        conn.close()


@contextmanager
def database_cursor(dictionary=False):
    conn = connect()
    cursor = conn.cursor(dictionary=dictionary)
    try:
        yield conn, cursor
    finally:
        cursor.close()
        conn.close()


def validate_schedule(data):
    if not isinstance(data, dict):
        return "El cuerpo debe ser un objeto JSON."
    nombre = data.get("nombre", "")
    color = data.get("color", "")
    bloques = data.get("bloques")
    if not isinstance(nombre, str) or not nombre.strip() or len(nombre.strip()) > 100:
        return "El nombre es obligatorio y debe tener máximo 100 caracteres."
    if not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        return "El color debe ser un hexadecimal válido, por ejemplo #E8A87C."
    if not isinstance(bloques, list) or not bloques:
        return "Agrega al menos un bloque de clase."
    dias = {"Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"}
    for bloque in bloques:
        if not isinstance(bloque, dict):
            return "Cada bloque debe ser un objeto."
        if bloque.get("dia") not in dias:
            return "El día de un bloque no es válido."
        if not all(isinstance(bloque.get(key), str) and bloque[key].strip()
                   for key in ("sede", "materia", "inicio", "fin")):
            return "Cada clase necesita sede, materia y horas."
        if bloque["sede"] not in SEDES:
            return "La sede no es válida. Selecciona una de la lista."
        if bloque["materia"] not in MATERIAS:
            return "La materia no es válida. Selecciona una de la lista."
        if not re.fullmatch(r"\d{2}:\d{2}", bloque["inicio"]) or not re.fullmatch(r"\d{2}:\d{2}", bloque["fin"]):
            return "Las horas deben usar el formato HH:MM."
        for hour in (bloque["inicio"], bloque["fin"]):
            hh, mm = map(int, hour.split(":"))
            if hh > 23 or mm > 59:
                return "Las horas deben ser válidas en formato de 24 horas."
        if bloque["fin"] <= bloque["inicio"]:
            return "La hora final debe ser posterior a la inicial."
    return None


@app.get("/api/health")
def health():
    try:
        with database_cursor() as (_, cursor):
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return jsonify({"ok": True, "database": DB_CONFIG["database"]})
    except mysql.connector.Error:
        app.logger.exception("No se pudo conectar con MySQL")
        return jsonify({"error": "No se pudo conectar con MySQL."}), 503


@app.get("/api/sedes")
def get_sedes():
    return jsonify(SEDES)


@app.get("/api/materias")
def get_materias():
    return jsonify(MATERIAS)


def database_day(day):
    return {"Miércoles": "Miercoles", "Sábado": "Sabado"}.get(day, day)


def api_day(day):
    return {"Miercoles": "Miércoles", "Sabado": "Sábado"}.get(day, day)


@app.get("/api/estudiantes")
def get_students():
    try:
        with database_cursor(dictionary=True) as (_, cursor):
            cursor.execute("""
                SELECT e.id_estudiante, e.nombre, e.color, h.dia,
                       s.nombre_sede AS sede, m.nombre_materia AS materia,
                       TIME_FORMAT(h.hora_inicio, '%H:%i') AS inicio,
                       TIME_FORMAT(h.hora_fin, '%H:%i') AS fin
                FROM estudiantes e
                LEFT JOIN huecos h ON h.id_estudiante = e.id_estudiante
                LEFT JOIN sedes s ON s.id_sede = h.id_sede
                LEFT JOIN materias m ON m.id_materia = h.id_materia
                ORDER BY e.nombre, h.id_hueco
            """)
            rows = cursor.fetchall()
        students = {}
        for row in rows:
            student = students.setdefault(row["id_estudiante"], {
                "nombre": row["nombre"], "color": row["color"], "bloques": []
            })
            if row["dia"]:
                student["bloques"].append({
                    "dia": api_day(row["dia"]), "sede": row["sede"], "materia": row["materia"],
                    "inicio": row["inicio"], "fin": row["fin"],
                })
        return jsonify(list(students.values()))
    except mysql.connector.Error:
        app.logger.exception("No se pudieron consultar los estudiantes")
        return jsonify({"error": "No se pudieron consultar los horarios."}), 503


@app.post("/api/estudiantes")
def save_student():
    data = request.get_json(silent=True)
    error = validate_schedule(data)
    if error:
        return jsonify({"error": error}), 400
    nombre = data["nombre"].strip()
    color = data["color"].upper()
    try:
        with database_cursor() as (conn, cursor):
            cursor.execute(
                "SELECT id_estudiante FROM estudiantes WHERE nombre = %s", (nombre,)
            )
            existing = cursor.fetchone()
            cursor.execute(
                "SELECT id_estudiante FROM estudiantes WHERE color = %s AND nombre <> %s",
                (color, nombre),
            )
            if cursor.fetchone():
                return jsonify({"error": "Ese color ya está asignado a otro estudiante."}), 409
            if existing:
                student_id = existing[0]
                cursor.execute(
                    "UPDATE estudiantes SET color = %s WHERE id_estudiante = %s",
                    (color, student_id),
                )
                cursor.execute("DELETE FROM huecos WHERE id_estudiante = %s", (student_id,))
            else:
                cursor.execute("INSERT INTO estudiantes (nombre, color) VALUES (%s, %s)", (nombre, color))
                student_id = cursor.lastrowid
            cursor.executemany(
                "INSERT INTO sedes (nombre_sede) VALUES (%s) "
                "ON DUPLICATE KEY UPDATE id_sede = LAST_INSERT_ID(id_sede)",
                [(b["sede"].strip(),) for b in data["bloques"]],
            )
            cursor.executemany(
                "INSERT INTO materias (nombre_materia) VALUES (%s) "
                "ON DUPLICATE KEY UPDATE id_materia = LAST_INSERT_ID(id_materia)",
                [(b["materia"].strip(),) for b in data["bloques"]],
            )
            for bloque in data["bloques"]:
                cursor.execute("SELECT id_sede FROM sedes WHERE nombre_sede = %s", (bloque["sede"].strip(),))
                sede_id = cursor.fetchone()[0]
                cursor.execute(
                    "SELECT id_materia FROM materias WHERE nombre_materia = %s",
                    (bloque["materia"].strip(),),
                )
                materia_id = cursor.fetchone()[0]
                cursor.execute(
                    "INSERT INTO huecos "
                    "(id_estudiante, id_sede, id_materia, dia, hora_inicio, hora_fin) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (student_id, sede_id, materia_id, database_day(bloque["dia"]),
                     bloque["inicio"], bloque["fin"]),
                )
            conn.commit()
        return jsonify({"ok": True, "nombre": nombre, "color": color}), 201
    except IntegrityError as error:
        if error.errno == 1062:
            return jsonify({"error": "Ese nombre o color ya está asignado a otro estudiante."}), 409
        app.logger.exception("Error de integridad al guardar")
        return jsonify({"error": "No se pudo guardar el horario."}), 500
    except mysql.connector.Error:
        app.logger.exception("No se pudo guardar el horario")
        return jsonify({"error": "No se pudo guardar el horario en MySQL."}), 503


@app.get("/api/huecos")
def get_huecos():
    """Calcula los huecos: intervalos libres entre la primera y la ultima clase de cada dia."""
    try:
        with database_cursor(dictionary=True) as (_, cursor):
            cursor.execute("""
                SELECT e.nombre, e.color, h.dia,
                       m.nombre_materia AS materia,
                       TIME_FORMAT(h.hora_inicio, '%H:%i') AS inicio,
                       TIME_FORMAT(h.hora_fin, '%H:%i') AS fin
                FROM estudiantes e
                JOIN huecos h ON h.id_estudiante = e.id_estudiante
                JOIN materias m ON m.id_materia = h.id_materia
                ORDER BY e.nombre, h.dia, h.hora_inicio
            """)
            rows = cursor.fetchall()
    except mysql.connector.Error:
        app.logger.exception("No se pudieron calcular los huecos")
        return jsonify({"error": "No se pudieron calcular los huecos."}), 503

    def to_min(hour):
        hh, mm = map(int, hour.split(":"))
        return hh * 60 + mm

    def to_hhmm(minutes):
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    por_dia = {}
    for row in rows:
        key = (row["nombre"], row["dia"])
        por_dia.setdefault(key, {
            "nombre": row["nombre"], "color": row["color"],
            "dia": api_day(row["dia"]), "bloques": [],
        })["bloques"].append(row)

    resultado = []
    for entry in por_dia.values():
        bloques = sorted(entry["bloques"], key=lambda b: b["inicio"])
        huecos = []
        for antes, despues in zip(bloques, bloques[1:]):
            fin_antes = to_min(max(b["fin"] for b in bloques if b["inicio"] <= antes["inicio"]))
            inicio_despues = to_min(despues["inicio"])
            if inicio_despues > fin_antes:
                huecos.append({
                    "inicio": to_hhmm(fin_antes),
                    "fin": to_hhmm(inicio_despues),
                    "materia_antes": antes["materia"],
                    "materia_despues": despues["materia"],
                })
        if huecos:
            resultado.append({
                "nombre": entry["nombre"], "color": entry["color"],
                "dia": entry["dia"], "huecos": huecos,
            })
    return jsonify(resultado)


@app.get("/api/cruce")
def get_cruce():
    """Cruce entre estudiantes seleccionados.
    tipo=clases: INNER JOIN por dia, materia, sede y horario identico.
    tipo=huecos: interseccion de los huecos calculados de todos."""
    nombres = [n.strip() for n in request.args.get("nombres", "").split(",") if n.strip()]
    tipo = request.args.get("tipo", "clases")
    if len(nombres) < 2:
        return jsonify({"error": "Selecciona al menos dos estudiantes."}), 400
    if tipo not in ("clases", "huecos"):
        return jsonify({"error": "Tipo de cruce no valido."}), 400
    fmt = ",".join(["%s"] * len(nombres))
    try:
        with database_cursor(dictionary=True) as (_, cursor):
            if tipo == "clases":
                cursor.execute(f"""
                    SELECT h.dia, s.nombre_sede AS sede, m.nombre_materia AS materia,
                           TIME_FORMAT(h.hora_inicio, '%H:%i') AS inicio,
                           TIME_FORMAT(h.hora_fin, '%H:%i') AS fin,
                           GROUP_CONCAT(e.nombre ORDER BY e.nombre SEPARATOR '|') AS participantes
                    FROM huecos h
                    JOIN estudiantes e ON e.id_estudiante = h.id_estudiante
                    JOIN sedes s ON s.id_sede = h.id_sede
                    JOIN materias m ON m.id_materia = h.id_materia
                    WHERE e.nombre IN ({fmt})
                    GROUP BY h.dia, s.nombre_sede, m.nombre_materia, h.hora_inicio, h.hora_fin
                    HAVING COUNT(DISTINCT e.nombre) = %s
                    ORDER BY h.dia, h.hora_inicio
                """, (*nombres, len(nombres)))
                return jsonify([
                    {**row, "dia": api_day(row["dia"])} for row in cursor.fetchall()
                ])
            cursor.execute(f"""
                SELECT e.nombre, h.dia,
                       TIME_FORMAT(h.hora_inicio, '%H:%i') AS inicio,
                       TIME_FORMAT(h.hora_fin, '%H:%i') AS fin
                FROM huecos h
                JOIN estudiantes e ON e.id_estudiante = h.id_estudiante
                WHERE e.nombre IN ({fmt})
                ORDER BY h.dia, h.hora_inicio
            """, nombres)
            rows = cursor.fetchall()
    except mysql.connector.Error:
        app.logger.exception("No se pudo calcular el cruce")
        return jsonify({"error": "No se pudo calcular el cruce."}), 503

    # huecos por estudiante y dia: intervalos libres entre primera y ultima clase
    por_dia = {}
    for row in rows:
        if row["nombre"] not in nombres:
            continue
        key = (row["dia"], row["nombre"])
        por_dia.setdefault(key, []).append(row)

    huecos_por_dia = {}
    for (dia, nombre), bloques in por_dia.items():
        huecos = []
        limite = None
        for b in sorted(bloques, key=lambda x: x["inicio"]):
            if limite is not None and b["inicio"] > limite:
                huecos.append([limite, b["inicio"]])
            limite = b["fin"] if limite is None else max(limite, b["fin"])
        huecos_por_dia.setdefault(dia, {})[nombre] = huecos

    resultado = []
    for dia, por_nombre in huecos_por_dia.items():
        comunes = None
        for nombre in nombres:
            huecos = por_nombre.get(nombre)
            if huecos is None:
                comunes = []
                break
            if comunes is None:
                comunes = [list(h) for h in huecos]
                continue
            nuevas = []
            for a_ini, a_fin in comunes:
                for b_ini, b_fin in huecos:
                    ini, fin = max(a_ini, b_ini), min(a_fin, b_fin)
                    if ini < fin:
                        nuevas.append([ini, fin])
            comunes = nuevas
        for ini, fin in (comunes or []):
            resultado.append({
                "dia": api_day(dia), "sede": "", "materia": "Hueco en comun",
                "inicio": ini, "fin": fin,
                "participantes": "|".join(sorted(nombres)),
            })
    return jsonify(resultado)


@app.delete("/api/estudiantes/<path:nombre>")
def delete_student(nombre):
    try:
        with database_cursor() as (conn, cursor):
            cursor.execute("DELETE FROM estudiantes WHERE nombre = %s", (nombre,))
            deleted = cursor.rowcount
            conn.commit()
        if not deleted:
            return jsonify({"error": "No se encontró ese estudiante."}), 404
        return jsonify({"ok": True})
    except mysql.connector.Error:
        app.logger.exception("No se pudo eliminar el estudiante")
        return jsonify({"error": "No se pudo eliminar el estudiante."}), 503

if __name__ == "__main__":
    try:
        initialize_database()
    except mysql.connector.Error:
        app.logger.exception("No se pudo preparar la base de datos Parchologia")
        raise
    app.run(host=os.getenv("API_HOST", "127.0.0.1"), port=int(os.getenv("API_PORT", "5000")), debug=False)
