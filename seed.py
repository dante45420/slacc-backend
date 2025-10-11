from app import create_app
from app.extensions import db
from app.models.news import News
from app.models.application import Application
from app.models.user import User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
  db.drop_all(); db.create_all()
  # Owner admin se crea por bootstrap; añadimos un miembro de ejemplo
  member = User(email="miembro@example.com", name="Miembro Demo", password_hash=generate_password_hash("demo1234"), role="member", membership_type="normal", is_active=True, payment_status="paid")
  db.session.add(member)
  # Noticias demo
  db.session.add_all([
    News(title="Noticia publicada", excerpt="Resumen", content="Contenido", status="published", order_index=0),
    News(title="Noticia pendiente", excerpt="Resumen 2", content="Contenido 2", status="pending", order_index=1)
  ])
  db.session.commit()
  print("Base de datos creada. Usa el panel admin para crear contenido.")


