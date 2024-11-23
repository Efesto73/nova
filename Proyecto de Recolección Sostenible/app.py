from flask import Flask, render_template, request, jsonify, redirect, url_for
from sklearn.neighbors import KNeighborsClassifier
import sqlite3
import numpy as np

# Configuración inicial
app = Flask(__name__)

# Función para interactuar con la base de datos
def ejecutar_query(query, params=()):
    with sqlite3.connect('recoleccion.db') as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor

# Crear tabla si no existe
ejecutar_query("""
    CREATE TABLE IF NOT EXISTS puntos_recoleccion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        latitud REAL,
        longitud REAL,
        hora INTEGER,
        actividad INTEGER
    )
""")

from flask import Flask, render_template, request, jsonify, redirect, url_for
from sklearn.neighbors import KNeighborsClassifier
from flask_mail import Mail, Message
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
import numpy as np

# Configuración inicial
app = Flask(__name__)
app.secret_key = "super_secret_key"

# Configuración de base de datos
def ejecutar_query(query, params=()):
    with sqlite3.connect('recoleccion.db') as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor

# Configuración de correo
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'tu_correo@gmail.com'
app.config['MAIL_PASSWORD'] = 'tu_contraseña'
mail = Mail(app)

# Configuración de autenticación
login_manager = LoginManager()
login_manager.init_app(app)

# Modelo de usuario para autenticación
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    user = ejecutar_query("SELECT * FROM usuarios WHERE id=?", (user_id,)).fetchone()
    if user:
        return User(id=user[0], username=user[1], password=user[2])
    return None

# Crear tablas necesarias si no existen
ejecutar_query("""
    CREATE TABLE IF NOT EXISTS puntos_recoleccion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        latitud REAL,
        longitud REAL,
        hora INTEGER,
        actividad INTEGER
    )
""")
ejecutar_query("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )
""")

# Entrenar el modelo dinámico
def entrenar_modelo():
    datos = ejecutar_query("SELECT latitud, longitud, hora, actividad FROM puntos_recoleccion").fetchall()
    if len(datos) < 3:
        return None
    X = np.array([fila[:3] for fila in datos])
    y = np.array([fila[3] for fila in datos])
    modelo = KNeighborsClassifier(n_neighbors=3)
    modelo.fit(X, y)
    return modelo

# Rutas
@app.route("/")
def home():
    puntos = ejecutar_query("SELECT * FROM puntos_recoleccion").fetchall()
    return render_template("index.html", puntos=puntos)

@app.route("/predict", methods=["POST"])
@login_required
def predict():
    data = request.json
    ubicacion = data.get("ubicacion")
    hora = data.get("hora")
    modelo = entrenar_modelo()
    if modelo is None:
        return jsonify({"error": "No hay suficientes datos para entrenar el modelo."}), 400
    entrada = np.array([[ubicacion[0], ubicacion[1], hora]])
    prediccion = modelo.predict(entrada)
    return jsonify({"punto_sugerido": int(prediccion[0])})

@app.route("/add", methods=["POST"])
@login_required
def add_point():
    latitud = request.form.get("latitud")
    longitud = request.form.get("longitud")
    hora = request.form.get("hora")
    actividad = request.form.get("actividad")
    ejecutar_query(
        "INSERT INTO puntos_recoleccion (latitud, longitud, hora, actividad) VALUES (?, ?, ?, ?)",
        (latitud, longitud, hora, actividad)
    )
    return redirect(url_for("home"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = ejecutar_query("SELECT * FROM usuarios WHERE username=? AND password=?", (username, password)).fetchone()
        if user:
            login_user(User(id=user[0], username=user[1], password=user[2]))
            return redirect(url_for("home"))
        return "Usuario o contraseña incorrectos", 401
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/send_notification", methods=["POST"])
@login_required
def send_notification():
    email = request.form.get("email")
    mensaje = request.form.get("mensaje")
    msg = Message("Notificación de Recolección", sender="tu_correo@gmail.com", recipients=[email])
    msg.body = mensaje
    mail.send(msg)
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)