from app import create_app
from app.extensions import db
from app.models.news import News
from app.models.application import Application
from app.models.event import Event, EventEnrollment
from app.models.user import User
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import os

app = create_app()

with app.app_context():
  db.drop_all()
  db.create_all()
  
  # ===== USERS (6+ varied examples) =====
  users_data = [
    {
      "email": "carlos.lopez@example.com",
      "name": "Dr. Carlos López Martínez",
      "password": "demo1234",
      "role": "member",
      "membership_type": "normal",
      "is_active": True,
      "payment_status": "paid",
    },
    {
      "email": "ana.garcia@example.com",
      "name": "Dra. Ana García Rodríguez",
      "password": "demo1234",
      "role": "member",
      "membership_type": "joven",
      "is_active": True,
      "payment_status": "paid",
    },
    {
      "email": "jorge.silva@example.com",
      "name": "Dr. Jorge Silva Peña",
      "password": "demo1234",
      "role": "member",
      "membership_type": "gratuito",
      "is_active": True,
      "payment_status": "paid",
    },
    {
      "email": "maria.fernandez@example.com",
      "name": "Dra. María Fernández Cruz",
      "password": "demo1234",
      "role": "member",
      "membership_type": "normal",
      "is_active": True,
      "payment_status": "due",
    },
    {
      "email": "pedro.morales@example.com",
      "name": "Dr. Pedro Morales Gómez",
      "password": "demo1234",
      "role": "member",
      "membership_type": "joven",
      "is_active": False,
      "payment_status": "none",
    },
    {
      "email": "lucia.ramirez@example.com",
      "name": "Dra. Lucía Ramírez Sánchez",
      "password": "demo1234",
      "role": "member",
      "membership_type": "normal",
      "is_active": True,
      "payment_status": "paid",
    },
  ]
  
  user_objects = []
  for u in users_data:
    user = User()
    user.email = u["email"]
    user.name = u["name"]
    user.password_hash = generate_password_hash(u["password"])
    user.role = u["role"]
    user.membership_type = u["membership_type"]
    user.is_active = u["is_active"]
    user.payment_status = u["payment_status"]
    db.session.add(user)
    user_objects.append(user)
  
  db.session.flush()
  
  # Create admin user
  admin_user = User()
  admin_user.email = "danteparodi@slacc.info"
  admin_user.name = "Dante Parodi"
  admin_user.password_hash = generate_password_hash(os.getenv("OWNER_INITIAL_PASSWORD", "admin1234"))
  admin_user.role = "admin"
  admin_user.membership_type = "normal"
  admin_user.is_active = True
  admin_user.payment_status = "paid"
  db.session.add(admin_user)
  db.session.flush()
  
  # ===== NEWS (6+ varied examples) =====
  news_data = [
    {
      "title": "Nuevas técnicas en artroplastia de cadera",
      "excerpt": "Descubre los avances más recientes en el campo de la artroplastia",
      "content": "Contenido detallado sobre nuevas técnicas quirúrgicas y materiales innovadores...",
      "category": "articulos-cientificos",
      "status": "published",
      "order_index": 0,
    },
    {
      "title": "Congreso SLACC 2024: Inscripciones Abiertas",
      "excerpt": "El evento más importante del año cardiovascular llega en septiembre",
      "content": "Nos complace anunciar el congreso anual de SLACC con participación de expertos internacionales...",
      "category": "articulos-destacados",
      "status": "published",
      "order_index": 1,
    },
    {
      "title": "Estudios recientes sobre trauma de cadera",
      "excerpt": "Análisis de morbimortalidad en pacientes traumatizados",
      "content": "Presentamos los resultados de nuestro estudio multicéntrico sobre trauma de cadera...",
      "category": "articulos-cientificos",
      "status": "published",
      "order_index": 2,
    },
    {
      "title": "Cambios en las políticas de membresía",
      "excerpt": "Actualización importante para todos nuestros socios",
      "content": "A partir del próximo año, implementaremos nuevas categorías de membresía...",
      "category": "editoriales",
      "status": "published",
      "order_index": 3,
    },
    {
      "title": "Webinar: Complicaciones en cadera",
      "excerpt": "Cómo identificar y manejar complicaciones postquirúrgicas",
      "content": "Expertos compartirán su experiencia en el manejo de complicaciones...",
      "category": "articulos-destacados",
      "status": "published",
      "order_index": 4,
    },
    {
      "title": "Artículo pendiente de revisión",
      "excerpt": "Este artículo está en proceso de revisión editorial",
      "content": "Contenido bajo revisión por el equipo editorial...",
      "category": "articulos-cientificos",
      "status": "pending",
      "order_index": 5,
    },
  ]
  
  for n in news_data:
    news = News()
    news.title = n["title"]
    news.excerpt = n["excerpt"]
    news.content = n["content"]
    news.category = n["category"]
    news.status = n["status"]
    news.order_index = n["order_index"]
    if len(user_objects) > 0:
      news.created_by_user_id = user_objects[0].id
    db.session.add(news)
  
  # ===== EVENTS (6+ varied examples) =====
  events_data = [
    {
      "title": "Webinar: Abordajes Innovadores en Artroplastia",
      "description": "Un webinar interactivo sobre las últimas técnicas quirúrgicas",
      "instructor": "Dr. Felipe González",
      "duration_hours": 2,
      "format": "webinar",
      "location": "https://zoom.us/meeting",
      "max_students": 500,
      "price_member": 50,
      "price_non_member": 100,
      "price_joven": 25,
      "price_gratuito": 0,
      "start_date": datetime.now() + timedelta(days=7),
      "end_date": datetime.now() + timedelta(days=7, hours=2),
      "registration_deadline": datetime.now() + timedelta(days=5),
      "is_active": True,
    },
    {
      "title": "Curso Presencial: Cirugía de Preservación Avanzada",
      "description": "Curso intensivo de 3 días con práctica quirúrgica simulada",
      "instructor": "Dra. Valentina Rodríguez",
      "duration_hours": 24,
      "format": "presencial",
      "location": "Ciudad de México, México",
      "max_students": 30,
      "price_member": 500,
      "price_non_member": 800,
      "price_joven": 300,
      "price_gratuito": 100,
      "start_date": datetime.now() + timedelta(days=30),
      "end_date": datetime.now() + timedelta(days=32),
      "registration_deadline": datetime.now() + timedelta(days=25),
      "is_active": True,
    },
    {
      "title": "Webinar: Manejo de Complicaciones",
      "description": "Panel de expertos discutiendo complicaciones y sus soluciones",
      "instructor": "Dr. Roberto Díaz",
      "duration_hours": 1.5,
      "format": "webinar",
      "location": "https://zoom.us/meeting",
      "max_students": 300,
      "price_member": 30,
      "price_non_member": 60,
      "price_joven": 15,
      "price_gratuito": 0,
      "start_date": datetime.now() - timedelta(days=5),
      "end_date": datetime.now() - timedelta(days=5, hours=1.5),
      "registration_deadline": datetime.now() - timedelta(days=7),
      "is_active": True,
    },
    {
      "title": "Congreso SLACC 2024",
      "description": "El evento más importante del año con participación internacional",
      "instructor": "Múltiples expertos",
      "duration_hours": 48,
      "format": "presencial",
      "location": "Santiago, Chile",
      "max_students": 1000,
      "price_member": 600,
      "price_non_member": 1200,
      "price_joven": 300,
      "price_gratuito": 150,
      "start_date": datetime.now() + timedelta(days=60),
      "end_date": datetime.now() + timedelta(days=62),
      "registration_deadline": datetime.now() + timedelta(days=50),
      "is_active": True,
    },
    {
      "title": "Taller: Técnicas Mínimamente Invasivas",
      "description": "Aprendizaje de técnicas de cirugía mínimamente invasiva",
      "instructor": "Dr. Andrés Martínez",
      "duration_hours": 8,
      "format": "presencial",
      "location": "Buenos Aires, Argentina",
      "max_students": 20,
      "price_member": 400,
      "price_non_member": 700,
      "price_joven": 200,
      "price_gratuito": 50,
      "start_date": datetime.now() + timedelta(days=45),
      "end_date": datetime.now() + timedelta(days=45, hours=8),
      "registration_deadline": datetime.now() + timedelta(days=40),
      "is_active": True,
    },
    {
      "title": "Webinar: Biomecánica de Implantes",
      "description": "Entendiendo la biomecánica detrás de los implantes modernos",
      "instructor": "Dr. Isaac Cohen",
      "duration_hours": 2,
      "format": "webinar",
      "location": "https://zoom.us/meeting",
      "max_students": 400,
      "price_member": 40,
      "price_non_member": 80,
      "price_joven": 20,
      "price_gratuito": 0,
      "start_date": datetime.now() + timedelta(days=14),
      "end_date": datetime.now() + timedelta(days=14, hours=2),
      "registration_deadline": datetime.now() + timedelta(days=12),
      "is_active": True,
    },
  ]
  
  event_objects = []
  for e in events_data:
    event = Event()
    event.title = e["title"]
    event.description = e["description"]
    event.instructor = e["instructor"]
    event.duration_hours = e["duration_hours"]
    event.format = e["format"]
    event.location = e["location"]
    event.max_students = e["max_students"]
    event.price_member = e["price_member"]
    event.price_non_member = e["price_non_member"]
    event.price_joven = e["price_joven"]
    event.price_gratuito = e["price_gratuito"]
    event.start_date = e["start_date"]
    event.end_date = e["end_date"]
    event.registration_deadline = e["registration_deadline"]
    event.is_active = e["is_active"]
    db.session.add(event)
    event_objects.append(event)
  
  db.session.flush()
  
  # ===== APPLICATIONS (6+ varied examples) =====
  applications_data = [
    {
      "name": "Dr. Javier Herrera López",
      "email": "javier.herrera@example.com",
      "phone": "+34 912 345 678",
      "motivation": "Deseo unirme para ampliar mis conocimientos y conectar con colegas",
      "specialization": "Artroplastia de cadera",
      "experience_years": 10,
      "membership_type": "normal",
      "status": "paid",
    },
    {
      "name": "Dra. Sofía Mendoza García",
      "email": "sofia.mendoza@example.com",
      "phone": "+56 2 1234 5678",
      "motivation": "Soy residente y quiero ser parte de la comunidad SLACC",
      "specialization": "Trauma de cadera",
      "experience_years": 2,
      "membership_type": "joven",
      "status": "payment_pending",
    },
    {
      "name": "Dr. Enrique Moreno Ruiz",
      "email": "enrique.moreno@example.com",
      "phone": "+57 1 234 5678",
      "motivation": "Busco actualizar mis conocimientos en cirugía de preservación",
      "specialization": "Cirugía de preservación",
      "experience_years": 15,
      "membership_type": "normal",
      "status": "pending",
    },
    {
      "name": "Dra. Gabriela Ortiz López",
      "email": "gabriela.ortiz@example.com",
      "phone": "+51 1 2345 678",
      "motivation": "Profesional jubilado interesado en mantenerme actualizado",
      "specialization": "Artroplastia y trauma",
      "experience_years": 30,
      "membership_type": "gratuito",
      "status": "paid",
    },
    {
      "name": "Dr. Ricardo Fuentes Soto",
      "email": "ricardo.fuentes@example.com",
      "phone": "+55 11 98765 4321",
      "motivation": "Deseo acceder a los recursos educativos de SLACC",
      "specialization": "Complicaciones de cadera",
      "experience_years": 8,
      "membership_type": "normal",
      "status": "rejected",
      "resolution_note": "Solicitado ser reevaluado en 6 meses",
    },
    {
      "name": "Dra. Carla Vásquez Martín",
      "email": "carla.vasquez@example.com",
      "phone": "+502 7654 3210",
      "motivation": "Especialista buscando networking internacional",
      "specialization": "Biomecánica de implantes",
      "experience_years": 12,
      "membership_type": "normal",
      "status": "pending",
    },
  ]
  
  for a in applications_data:
    app = Application()
    app.name = a["name"]
    app.email = a["email"]
    app.phone = a["phone"]
    app.motivation = a["motivation"]
    app.specialization = a["specialization"]
    app.experience_years = a["experience_years"]
    app.membership_type = a["membership_type"]
    app.status = a["status"]
    if a["status"] == "rejected":
      app.resolution_note = a.get("resolution_note", "")
      app.decided_at = datetime.now() - timedelta(days=10)
    elif a["status"] == "paid":
      app.decided_at = datetime.now() - timedelta(days=20)
    db.session.add(app)
  
  db.session.flush()
  
  # ===== EVENT ENROLLMENTS (8+ varied examples) =====
  if len(event_objects) > 0 and len(user_objects) > 0:
    enrollments_data = [
      {
        "event_idx": 0,
        "user_idx": 0,
        "student_name": "Dr. Carlos López",
        "student_email": "carlos.lopez@example.com",
        "student_phone": "+34 912 345 678",
        "payment_status": "paid",
        "payment_amount": 50,
        "membership_type": "normal",
        "is_member": True,
      },
      {
        "event_idx": 0,
        "user_idx": 1,
        "student_name": "Dra. Ana García",
        "student_email": "ana.garcia@example.com",
        "student_phone": "+55 11 98765 4321",
        "payment_status": "paid",
        "payment_amount": 25,
        "membership_type": "joven",
        "is_member": True,
      },
      {
        "event_idx": 1,
        "user_idx": None,
        "student_name": "Dr. Desconocido No Socio",
        "student_email": "nosocio@example.com",
        "student_phone": "+1 234 567 8900",
        "payment_status": "pending",
        "payment_amount": 800,
        "membership_type": None,
        "is_member": False,
      },
      {
        "event_idx": 1,
        "user_idx": 2,
        "student_name": "Dr. Jorge Silva",
        "student_email": "jorge.silva@example.com",
        "student_phone": "+56 2 1234 5678",
        "payment_status": "paid",
        "payment_amount": 100,
        "membership_type": "gratuito",
        "is_member": True,
      },
      {
        "event_idx": 2,
        "user_idx": 3,
        "student_name": "Dra. María Fernández",
        "student_email": "maria.fernandez@example.com",
        "student_phone": "+57 1 234 5678",
        "payment_status": "paid",
        "payment_amount": 30,
        "membership_type": "normal",
        "is_member": True,
      },
      {
        "event_idx": 3,
        "user_idx": 5,
        "student_name": "Dra. Lucía Ramírez",
        "student_email": "lucia.ramirez@example.com",
        "student_phone": "+51 1 2345 678",
        "payment_status": "paid",
        "payment_amount": 600,
        "membership_type": "normal",
        "is_member": True,
      },
      {
        "event_idx": 4,
        "user_idx": 0,
        "student_name": "Dr. Carlos López",
        "student_email": "carlos.lopez@example.com",
        "student_phone": "+34 912 345 678",
        "payment_status": "paid",
        "payment_amount": 400,
        "membership_type": "normal",
        "is_member": True,
      },
      {
        "event_idx": 5,
        "user_idx": 1,
        "student_name": "Dra. Ana García",
        "student_email": "ana.garcia@example.com",
        "student_phone": "+55 11 98765 4321",
        "payment_status": "pending",
        "payment_amount": 20,
        "membership_type": "joven",
        "is_member": True,
      },
    ]
    
    for e in enrollments_data:
      enrollment = EventEnrollment()
      enrollment.event_id = event_objects[e["event_idx"]].id
      if e["user_idx"] is not None:
        enrollment.user_id = user_objects[e["user_idx"]].id
      enrollment.student_name = e["student_name"]
      enrollment.student_email = e["student_email"]
      enrollment.student_phone = e["student_phone"]
      enrollment.payment_status = e["payment_status"]
      enrollment.payment_amount = e["payment_amount"]
      enrollment.membership_type = e["membership_type"]
      enrollment.is_member = e["is_member"]
      if e["payment_status"] == "paid":
        enrollment.payment_date = datetime.now() - timedelta(days=5)
      db.session.add(enrollment)
  
  db.session.commit()
  print("✓ Base de datos sembrada exitosamente con datos variados!")
  print(f"  - {len(user_objects)} usuarios creados")
  print(f"  - {len(news_data)} noticias creadas")
  print(f"  - {len(event_objects)} eventos creados")
  print(f"  - {len(applications_data)} aplicaciones de membresía creadas")



