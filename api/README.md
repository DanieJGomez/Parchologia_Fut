# API de horarios Parchologia

La API guarda los horarios en MySQL, en la base `Parchologia`, usando las tablas `estudiantes`, `sedes`, `materias` y `huecos`. Al iniciar, crea la base y esas tablas si aún no existen. Si ya tienes el esquema con `estudiantes.id_estudiante` y las relaciones de `huecos`, la API reutiliza esas tablas y conserva sus datos. El usuario MySQL configurado necesita permiso para crear la base la primera vez.

## Iniciar

Desde esta carpeta, crea un entorno virtual e instala las dependencias:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Configura en `.env` la contraseña y usuario de MySQL. Luego inicia el servidor:

```powershell
py app.py
```

La aplicación web usa `http://127.0.0.1:5000/api`. Si el servidor está en otro equipo, cambia `API_URL` al inicio del script de `index.html` por la dirección de ese servidor y configura `API_HOST=0.0.0.0`.

## Rutas

- `GET /api/health`: comprueba la conexión con MySQL.
- `GET /api/sedes`: devuelve la lista predefinida de sedes.
- `GET /api/materias`: devuelve la lista predefinida de materias.
- `GET /api/estudiantes`: lista estudiantes y sus bloques.
- `GET /api/huecos`: calcula los huecos de cada estudiante por día (intervalos libres entre su primera y última clase). Responde `[{ nombre, color, dia, huecos: [{ inicio, fin, materia_antes, materia_despues }] }]`.
- `GET /api/cruce?nombres=A,B&tipo=clases|huecos`: cruce (inner join) entre los estudiantes seleccionados. Con `tipo=clases` devuelve los bloques con misma materia, sede y horario que comparten **todos**; con `tipo=huecos`, la intersección de sus huecos. Cada fila incluye el campo `participantes` separado por `|`.
- `POST /api/estudiantes`: crea o actualiza el horario. Recibe `{ "nombre", "color", "bloques" }`. La sede y la materia de cada bloque deben pertenecer a las listas predefinidas (`GET /api/sedes` y `GET /api/materias`); si no, la API responde `400`.
- `DELETE /api/estudiantes/<nombre>`: elimina al estudiante y sus bloques.

El color se almacena en formato hexadecimal; la API responde `409` si ya está asignado a otro estudiante. La API convierte los días `Miércoles` y `Sábado` enviados por la aplicación a `Miercoles` y `Sabado` en MySQL, y los vuelve a presentar con tilde al consultar los horarios.
