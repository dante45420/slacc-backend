import os
from app import create_app
from app.extensions import db
from app.models.user import User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    email = os.getenv("OWNER_EMAIL")
    password = os.getenv("OWNER_INITIAL_PASSWORD")
    if not email or not password:
        print("[ensure_owner] OWNER_EMAIL u OWNER_INITIAL_PASSWORD no definidos, omitiendo.")
    else:
        existing = User.query.filter_by(email=email).first()
        if existing:
            print(f"[ensure_owner] Usuario {email} ya existe. Nada que hacer.")
        else:
            user = User()
            user.email = email
            user.name = "Owner"
            user.password_hash = generate_password_hash(password)
            user.role = "admin"
            user.is_active = True
            user.payment_status = "paid"
            db.session.add(user)
            db.session.commit()
            print(f"[ensure_owner] Usuario admin {email} creado.")
