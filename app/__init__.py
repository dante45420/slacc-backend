import os
from datetime import datetime, timedelta
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

from .extensions import db, jwt
from .models.user import User
from .models.application import Application
from .models.news import News
from .routes.auth import auth_bp
from .routes.public import public_bp
from .routes.admin import admin_bp
from .routes.events import events_bp
from .routes.courses import courses_bp


def create_app():
    load_dotenv()
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///slac.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # Limites de subida para formularios/archivos (evita 413)
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH_MB", "32")) * 1024 * 1024
    # Werkzeug usa este límite para datos de formulario en memoria
    app.config["MAX_FORM_MEMORY_SIZE"] = int(os.getenv("MAX_FORM_MEMORY_SIZE_MB", "32")) * 1024 * 1024
    
    # JWT Configuration para Flask-JWT-Extended 4.6.0
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET", "change-this-secret")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=3)

    # CORS(app, resources={r"/api/*": {"origins": os.getenv("CORS_ORIGINS", "*")}})
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Uploads (simula bucket)
    app.config["UPLOAD_DIR"] = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "..", "uploads"))
    upload_dir = os.path.abspath(app.config["UPLOAD_DIR"]) 
    os.makedirs(upload_dir, exist_ok=True)

    db.init_app(app)
    jwt.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(courses_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    _register_static_uploads(app)

    with app.app_context():
        db.create_all()
        _bootstrap_owner()

    return app


def _bootstrap_owner():
    from werkzeug.security import generate_password_hash

    owner_email = os.getenv("OWNER_EMAIL")
    owner_password = os.getenv("OWNER_INITIAL_PASSWORD")
    if not owner_email or not owner_password:
        return
    existing = User.query.filter_by(email=owner_email).first()
    if existing:
        return
    owner = User()
    owner.email = owner_email
    owner.name = "Owner"
    owner.password_hash = generate_password_hash(owner_password)
    owner.role = "admin"
    owner.is_active = True
    owner.payment_status = "paid"
    db.session.add(owner)
    db.session.commit()


# Ruta estática para servir archivos subidos
def _register_static_uploads(app: Flask):
    upload_dir = os.path.abspath(app.config["UPLOAD_DIR"]) 
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(upload_dir, filename)
    
    # También registrar como ruta estática para mayor compatibilidad
    app.static_folder = upload_dir
    app.static_url_path = '/uploads'


