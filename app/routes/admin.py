import os
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models.application import Application
from ..models.news import News
from ..models.user import User
from ..models.course import Course, CourseEnrollment

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.get("/applications")
@jwt_required()
def list_applications():
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403
  
  items = Application.query.order_by(Application.created_at.desc()).all()
  return jsonify([
    {
      "id": a.id,
      "name": a.name,
      "email": a.email,
      "phone": a.phone,
      "motivation": a.motivation,
      "specialization": a.specialization,
      "experience_years": a.experience_years,
      "membership_type": a.membership_type,
      "status": a.status,
      "resolution_note": a.resolution_note,
      "decided_at": a.decided_at.isoformat() if a.decided_at else None,
      "created_at": a.created_at.isoformat(),
    }
    for a in items
  ])


@admin_bp.get("/applications/<int:app_id>")
@jwt_required()
def get_application(app_id):
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403
  
  app = Application.query.get_or_404(app_id)
  return jsonify({
    "id": app.id,
    "name": app.name,
    "email": app.email,
    "phone": app.phone,
    "motivation": app.motivation,
    "specialization": app.specialization,
    "experience_years": app.experience_years,
    "membership_type": app.membership_type,
    "status": app.status,
    "resolution_note": app.resolution_note,
    "decided_at": app.decided_at.isoformat() if app.decided_at else None,
    "created_at": app.created_at.isoformat(),
  })


@admin_bp.post("/applications/<int:app_id>/approve")
@jwt_required()
def approve_application(app_id):
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403

  from datetime import datetime
  app_row = Application.query.get_or_404(app_id)
  if app_row.status != "pending":
    return jsonify({"message": "La solicitud ya fue resuelta"}), 400
  
  # Actualizar la aplicación con el tipo de membresía seleccionado
  data = request.get_json() or {}
  membership_type = data.get("membership_type", "normal")
  
  app_row.status = "payment_pending"  # Cambio: ahora queda esperando pago
  app_row.membership_type = membership_type
  app_row.resolution_note = data.get("note", "Aprobado - Esperando pago")
  app_row.decided_at = datetime.now(timezone.utc)
  
  db.session.commit()
  return jsonify({"message": "Aprobado - Esperando pago", "membership_type": membership_type})


@admin_bp.post("/applications/<int:app_id>/reject")
@jwt_required()
def reject_application(app_id):
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403

  app_row = Application.query.get_or_404(app_id)
  if app_row.status != "pending":
    return jsonify({"message": "La solicitud ya fue resuelta"}), 400
  app_row.status = "rejected"
  data = request.get_json() or {}
  app_row.resolution_note = data.get("note", "Rechazado")
  app_row.decided_at = datetime.now(timezone.utc)
  db.session.commit()
  return jsonify({"message": "Rechazado"})


@admin_bp.post("/applications/<int:app_id>/confirm-payment")
@jwt_required()
def confirm_payment(app_id):
  """Conciliar el pago y crear el usuario con credenciales"""
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403

  from datetime import datetime
  from werkzeug.security import generate_password_hash
  import secrets
  import string
  
  app_row = Application.query.get_or_404(app_id)
  if app_row.status != "payment_pending":
    return jsonify({"message": "La solicitud no está en estado de pago pendiente"}), 400
  
  # Verificar que no existe ya un usuario con ese email
  existing_user = User.query.filter_by(email=app_row.email).first()
  if existing_user:
    return jsonify({"message": "Ya existe un usuario con ese email"}), 400
  
  # Generar contraseña temporal
  temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
  
  # Crear el usuario
  new_user = User()
  new_user.email = app_row.email
  new_user.name = app_row.name
  new_user.password_hash = generate_password_hash(temp_password)
  new_user.role = "member"
  new_user.membership_type = app_row.membership_type
  new_user.is_active = True
  new_user.payment_status = "paid"
  db.session.add(new_user)
  
  # Actualizar la aplicación
  app_row.status = "paid"
  app_row.resolution_note = f"{app_row.resolution_note}\n\nPago confirmado - Usuario creado"
  app_row.decided_at = datetime.now(timezone.utc)
  
  db.session.commit()
  
  return jsonify({
    "message": "Pago confirmado - Usuario creado", 
    "credentials": {
      "email": new_user.email, 
      "password": temp_password,
      "membership_type": new_user.membership_type
    }
  })


@admin_bp.get("/news")
@jwt_required()
def admin_news_list():
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403

  items = News.query.order_by(News.created_at.desc()).all()
  return jsonify([n.to_dict() for n in items])


@admin_bp.post("/news/<int:news_id>/approve")
@jwt_required()
def admin_news_approve(news_id):
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403

  n = News.query.get_or_404(news_id)
  n.status = "published"
  db.session.commit()
  return jsonify({"message": "Publicada"})


@admin_bp.post("/news/<int:news_id>/reject")
@jwt_required()
def admin_news_reject(news_id):
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403

  n = News.query.get_or_404(news_id)
  n.status = "rejected"
  db.session.commit()
  return jsonify({"message": "Rechazada"})


@admin_bp.post("/news/reorder")
@jwt_required()
def reorder_news():
    """Reordenar noticias - evita duplicados de orden"""
    uid = int(get_jwt_identity())
    user = User.query.get(uid)
    if not user or user.role != "admin":
        return jsonify({"message":"Forbidden"}), 403
    
    try:
        data = request.get_json()
        if not data or not isinstance(data, list):
            return jsonify({"error": "Se requiere lista de cambios"}), 400
        
        # Procesar cada cambio de orden
        for change in data:
            news_id = change.get('id')
            new_order = change.get('order_index')
            
            if news_id is None or new_order is None:
                continue
                
            news = News.query.get(news_id)
            if not news:
                continue
            
            old_order = news.order_index
            news.order_index = new_order
            
            # Si hay otra noticia con el mismo orden, ajustarla
            conflicting_news = News.query.filter(
                News.id != news_id,
                News.order_index == new_order
            ).first()
            
            if conflicting_news:
                # Mover la noticia conflictiva en la dirección apropiada
                if new_order > old_order:
                    # Movimos hacia abajo, la conflictiva va hacia arriba
                    conflicting_news.order_index = new_order - 1
                else:
                    # Movimos hacia arriba, la conflictiva va hacia abajo
                    conflicting_news.order_index = new_order + 1
        
        db.session.commit()
        return jsonify({"message": "Orden actualizado"})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@admin_bp.post("/news/<int:news_id>/edit")
@jwt_required()
def edit_news(news_id):
    """Editar una noticia existente"""
    uid = int(get_jwt_identity())
    user = User.query.get(uid)
    if not user or user.role != "admin":
        return jsonify({"message":"Forbidden"}), 403
    
    news = News.query.get(news_id)
    if not news:
        return jsonify({"error": "Noticia no encontrada"}), 404
    
    try:
        # Procesar datos del formulario
        if 'title' in request.form:
            news.title = request.form['title']
        if 'excerpt' in request.form:
            news.excerpt = request.form['excerpt']
        if 'content' in request.form:
            news.content = request.form['content']
        if 'category' in request.form:
            news.category = (request.form['category'] or news.category).strip().lower()
        
        # Procesar imagen si se subió una nueva
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and image_file.filename:
                # Generar nombre único para la imagen
                import uuid
                filename = f"news-{uuid.uuid4().hex}.{image_file.filename.rsplit('.', 1)[1].lower()}"
                filepath = os.path.join(current_app.config["UPLOAD_DIR"], filename)
                
                # Guardar la nueva imagen
                image_file.save(filepath)
                
                # Eliminar imagen anterior si existe
                if news.image_url and os.path.exists(os.path.join(current_app.config["UPLOAD_DIR"], news.image_url.lstrip('/uploads/'))):
                    try:
                        os.remove(os.path.join(current_app.config["UPLOAD_DIR"], news.image_url.lstrip('/uploads/')))
                    except OSError:
                        pass
                
                # Actualizar URL de la imagen
                news.image_url = f"/uploads/{filename}"
        
        db.session.commit()
        return jsonify({"message": "Noticia actualizada correctamente"})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@admin_bp.get("/news/<int:news_id>/view")
@jwt_required()
def view_news(news_id):
    """Ver una noticia completa (admin puede ver cualquier estado)"""
    uid = int(get_jwt_identity())
    user = User.query.get(uid)
    if not user or user.role != "admin":
        return jsonify({"message":"Forbidden"}), 403
    
    news = News.query.get(news_id)
    if not news:
        return jsonify({"error": "Noticia no encontrada"}), 404
    
    return jsonify(news.to_dict())


@admin_bp.post("/users/<int:user_id>/mark-paid")
@jwt_required()
def admin_mark_paid(user_id):
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403

  u = User.query.get_or_404(user_id)
  u.payment_status = "paid"
  db.session.commit()
  return jsonify({"message": "Pago actualizado"})


@admin_bp.post("/users")
@jwt_required()
def admin_create_admin():
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403

  # Solo el owner puede crear admins
  owner_email = os.getenv("OWNER_EMAIL")
  if user.email != owner_email:
    return jsonify({"message": "Solo el owner puede crear administradores"}), 403
  
  data = request.get_json() or {}
  email = data.get("email", "").strip().lower()
  name = data.get("name", "Admin")
  password = data.get("password") or os.urandom(4).hex()
  if User.query.filter_by(email=email).first():
    return jsonify({"message": "Email ya existe"}), 400
  
  from werkzeug.security import generate_password_hash
  new_admin = User()
  new_admin.email = email
  new_admin.name = name
  new_admin.password_hash = generate_password_hash(password)
  new_admin.role = "admin"
  new_admin.is_active = True
  new_admin.payment_status = "paid"
  db.session.add(new_admin)
  db.session.commit()
  return jsonify({"message": "Admin creado", "credentials": {"email": email, "password": password}}), 201


@admin_bp.get("/users")
@jwt_required()
def admin_list_users():
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403

  users = User.query.order_by(User.created_at.desc()).all()
  return jsonify([user.to_safe_dict() for user in users])


# ===== Eventos (Cursos en vivo) =====
@admin_bp.get("/events")
@jwt_required()
def admin_events_list():
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403
  items = Course.query.order_by(Course.start_date.desc()).all()
  return jsonify([c.to_dict() for c in items])


@admin_bp.post("/events")
@jwt_required()
def admin_events_create():
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403

  data = request.get_json() or {}
  from datetime import datetime
  def parse(s):
    if not s:
      return None
    s = s.strip()
    # admitir 'YYYY-MM-DD'
    if len(s) == 10:
      s = s + "T00:00:00"
    return datetime.fromisoformat(s)
  course = Course()
  course.title = (data.get("title") or "").strip()
  course.description = (data.get("description") or "").strip()
  course.content = (data.get("content") or "").strip()
  course.instructor = (data.get("instructor") or "").strip()
  course.duration_hours = data.get("duration_hours")
  course.format = (data.get("format") or "webinar")
  course.max_students = data.get("max_students")
  course.price_member = float(data.get("price_member") or 0)
  course.price_non_member = float(data.get("price_non_member") or 0)
  course.price_joven = float(data.get("price_joven") or 0)
  course.price_gratuito = float(data.get("price_gratuito") or 0)
  course.start_date = parse(data.get("start_date"))
  course.end_date = parse(data.get("end_date"))
  course.registration_deadline = parse(data.get("registration_deadline"))
  course.is_active = bool(data.get("is_active", True))
  course.image_url = (data.get("image_url") or "").strip()
  db.session.add(course)
  db.session.commit()
  return jsonify(course.to_dict()), 201


@admin_bp.put("/events/<int:event_id>")
@jwt_required()
def admin_events_update(event_id: int):
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403

  course = Course.query.get_or_404(event_id)
  data = request.get_json() or {}
  from datetime import datetime
  def parse2(s, old):
    if not s:
      return old
    s = s.strip()
    if len(s) == 10:
      s = s + "T00:00:00"
    return datetime.fromisoformat(s)

  course.title = (data.get("title") or course.title).strip()
  course.description = (data.get("description") or course.description).strip()
  course.content = (data.get("content") or course.content).strip()
  course.instructor = (data.get("instructor") or course.instructor).strip()
  course.duration_hours = data.get("duration_hours", course.duration_hours)
  course.format = data.get("format", course.format)
  course.max_students = data.get("max_students", course.max_students)
  course.price_member = float(data.get("price_member", course.price_member))
  course.price_non_member = float(data.get("price_non_member", course.price_non_member))
  course.price_joven = float(data.get("price_joven", course.price_joven))
  course.price_gratuito = float(data.get("price_gratuito", course.price_gratuito))
  course.start_date = parse2(data.get("start_date"), course.start_date)
  course.end_date = parse2(data.get("end_date"), course.end_date)
  course.registration_deadline = parse2(data.get("registration_deadline"), course.registration_deadline)
  course.is_active = bool(data.get("is_active", course.is_active))
  course.image_url = (data.get("image_url") or course.image_url or "").strip()
  db.session.commit()
  return jsonify(course.to_dict())


@admin_bp.post("/events/<int:event_id>/image")
@jwt_required()
def admin_events_upload_image(event_id: int):
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403

  course = Course.query.get_or_404(event_id)
  if 'image' not in request.files:
    return jsonify({"error": "Archivo 'image' requerido"}), 400

  f = request.files['image']
  if not f or not f.filename:
    return jsonify({"error": "Archivo inválido"}), 400

  import os, uuid
  filename = f"event-{uuid.uuid4().hex}.{f.filename.rsplit('.', 1)[-1].lower()}"
  upload_dir = os.path.abspath(current_app.config["UPLOAD_DIR"]) 
  path = os.path.join(upload_dir, filename)
  f.save(path)
  course.image_url = f"/uploads/{filename}"
  db.session.commit()
  return jsonify({"image_url": course.image_url})


@admin_bp.delete("/events/<int:event_id>")
@jwt_required()
def admin_events_delete(event_id: int):
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403
  course = Course.query.get_or_404(event_id)
  has_enrollments = CourseEnrollment.query.filter_by(course_id=event_id).count() > 0
  if has_enrollments:
    return jsonify({"error": "No se puede eliminar con inscripciones"}), 400
  db.session.delete(course)
  db.session.commit()
  return jsonify({"message": "Eliminado"})


@admin_bp.get("/events/<int:event_id>/enrollments")
@jwt_required()
def admin_events_enrollments(event_id: int):
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403
  course = Course.query.get_or_404(event_id)
  enrollments = CourseEnrollment.query.filter_by(course_id=event_id).order_by(CourseEnrollment.enrollment_date.desc()).all()
  return jsonify({
    "event": course.to_dict(),
    "enrollments": [e.to_dict() for e in enrollments]
  })
@admin_bp.get("/users/<int:user_id>")
@jwt_required()
def admin_get_user(user_id: int):
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403

  u = User.query.get_or_404(user_id)
  data = u.to_safe_dict()
  data.update({
    "created_at": u.created_at.isoformat() if u.created_at else None,
  })
  return jsonify(data)


@admin_bp.put("/users/<int:user_id>")
@jwt_required()
def admin_update_user(user_id: int):
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403

  u = User.query.get_or_404(user_id)
  data = request.get_json() or {}

  # Campos permitidos a actualizar de forma simple
  if "name" in data:
    u.name = (data.get("name") or u.name).strip()
  if "is_active" in data:
    u.is_active = bool(data.get("is_active"))
  if "membership_type" in data and u.role == "member":
    u.membership_type = data.get("membership_type") or u.membership_type
  if "payment_status" in data and u.role == "member":
    u.payment_status = data.get("payment_status") or u.payment_status

  db.session.commit()
  return jsonify(u.to_safe_dict())


@admin_bp.post("/users/member")
@jwt_required()
def admin_create_member():
  """Crear un usuario miembro simple (uso interno admin)."""
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403

  data = request.get_json() or {}
  email = (data.get("email") or "").strip().lower()
  name = (data.get("name") or "").strip()
  password = data.get("password") or os.urandom(4).hex()
  membership_type = data.get("membership_type") or "normal"

  if not email or not name:
    return jsonify({"message": "Email y nombre son requeridos"}), 400
  if User.query.filter_by(email=email).first():
    return jsonify({"message": "Email ya existe"}), 400

  from werkzeug.security import generate_password_hash
  new_member = User()
  new_member.email = email
  new_member.name = name
  new_member.password_hash = generate_password_hash(password)
  new_member.role = "member"
  new_member.membership_type = membership_type
  new_member.is_active = True
  new_member.payment_status = data.get("payment_status") or "due"
  db.session.add(new_member)
  db.session.commit()

  resp = new_member.to_safe_dict()
  resp.update({"initial_password": password})
  return jsonify(resp), 201

