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
  member = User()
  member.email = "miembro@example.com"
  member.name = "Miembro Demo"
  member.password_hash = generate_password_hash("demo1234")
  member.role = "member"
  member.membership_type = "normal"
  member.is_active = True
  member.payment_status = "paid"
  db.session.add(member)
  # Noticias demo
  news1 = News()
  news1.title = "Noticia publicada"
  news1.excerpt = "Resumen"
  news1.content = "Contenido"
  news1.status = "published"
  news1.order_index = 0
  
  news2 = News()
  news2.title = "Noticia pendiente"
  news2.excerpt = "Resumen 2"
  news2.content = "Contenido 2"
  news2.status = "pending"
  news2.order_index = 1
  
  db.session.add_all([news1, news2])
  db.session.commit()
  print("Base de datos creada. Usa el panel admin para crear contenido.")


