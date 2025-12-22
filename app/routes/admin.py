import os
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from ..extensions import db
from ..models.application import Application
from ..models.news import News
from ..models.user import User
from ..models.event import Event, EventEnrollment
from ..utils.image_processing import process_uploaded_image

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.get("/applications")
@jwt_required()
def list_applications():
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403
  
  items = Application.query.order_by(Application.created_at.desc()).all()
  return jsonify([a.to_dict() for a in items])


@admin_bp.get("/applications/<int:app_id>")
@jwt_required()
def get_application(app_id):
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403
  
  app = Application.query.get_or_404(app_id)
  
  # Try to find the associated user (by email)
  associated_user = User.query.filter_by(email=app.email).first()
  
  response_data = app.to_dict()
  # Add initial_password if user exists
  response_data["initial_password"] = associated_user.initial_password if associated_user else None
  
  return jsonify(response_data)


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
  
  app_row = Application.query.get_or_404(app_id)
  if app_row.status != "payment_pending":
    return jsonify({"message": "La solicitud no está en estado de pago pendiente"}), 400
  
  # Verificar que no existe ya un usuario con ese email
  existing_user = User.query.filter_by(email=app_row.email).first()
  if existing_user:
    return jsonify({"message": "Ya existe un usuario con ese email"}), 400
  
  # Generar contraseña temporal secuencial: slacc001, slacc002, ...
  next_id = (db.session.query(func.max(User.id)).scalar() or 0) + 1
  temp_password = f"slacc{next_id:03d}"
  
  # Crear el usuario
  new_user = User()
  new_user.email = app_row.email
  new_user.name = app_row.name
  new_user.password_hash = generate_password_hash(temp_password)
  new_user.initial_password = temp_password  # Store plaintext for one-time display to admin
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
  
  # Return credentials for one-time display (admin should copy and send to user)
  # In production, this should be sent via email directly to the user
  return jsonify({
    "message": "Pago confirmado - Usuario creado exitosamente", 
    "user_id": new_user.id,
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
          category = (request.form['category'] or news.category).strip().lower()
          allowed = ("articulos-cientificos", "articulos-destacados", "editoriales")
          if category not in allowed:
            return jsonify({"error": "Categoría inválida"}), 400
          news.category = category
        
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
                
                # Optimize the image
                optimize_success, optimize_msg = process_uploaded_image(filepath, max_width=1920, max_height=1080, quality=85)
                if optimize_success:
                    print(f"Image optimized: {optimize_msg}")
                
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
  # TODO: Send credentials via secure email
  return jsonify({
    "message": "Admin creado. Credenciales deben ser enviadas de forma segura.",
    "user_id": new_admin.id,
    "email": email
  }), 201


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
  items = Event.query.order_by(Event.start_date.desc()).all()
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
  event = Event()
  event.title = (data.get("title") or "").strip()
  event.description = (data.get("description") or "").strip()
  event.content = (data.get("content") or "").strip()
  event.instructor = (data.get("instructor") or "").strip()
  event.duration_hours = data.get("duration_hours")
  event.format = (data.get("format") or "webinar")
  event.max_students = data.get("max_students")
  event.price_member = float(data.get("price_member") or 0)
  event.price_non_member = float(data.get("price_non_member") or 0)
  event.price_joven = float(data.get("price_joven") or 0)
  event.price_gratuito = float(data.get("price_gratuito") or 0)
  event.start_date = parse(data.get("start_date"))
  event.end_date = parse(data.get("end_date"))
  event.registration_deadline = parse(data.get("registration_deadline"))
  event.is_active = bool(data.get("is_active", True))
  event.image_url = (data.get("image_url") or "").strip()
  db.session.add(event)
  db.session.commit()
  return jsonify(event.to_dict()), 201


@admin_bp.put("/events/<int:event_id>")
@jwt_required()
def admin_events_update(event_id: int):
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403

  event = Event.query.get_or_404(event_id)
  data = request.get_json() or {}
  from datetime import datetime
  def parse2(s, old):
    if not s:
      return old
    s = s.strip()
    if len(s) == 10:
      s = s + "T00:00:00"
    return datetime.fromisoformat(s)

  # Update title (required field)
  new_title = data.get("title")
  if new_title:
    event.title = new_title.strip()
  
  # Update optional string fields
  new_description = data.get("description")
  if new_description is not None:
    event.description = new_description.strip() or None
  
  new_content = data.get("content")
  if new_content is not None:
    event.content = new_content.strip() or None
  
  new_instructor = data.get("instructor")
  if new_instructor is not None:
    event.instructor = new_instructor.strip() or None
  
  event.duration_hours = data.get("duration_hours", event.duration_hours)
  event.format = data.get("format", event.format)
  event.max_students = data.get("max_students", event.max_students)
  event.price_member = float(data.get("price_member", event.price_member))
  event.price_non_member = float(data.get("price_non_member", event.price_non_member))
  event.price_joven = float(data.get("price_joven", event.price_joven))
  event.price_gratuito = float(data.get("price_gratuito", event.price_gratuito))
  event.start_date = parse2(data.get("start_date"), event.start_date)
  event.end_date = parse2(data.get("end_date"), event.end_date)
  event.registration_deadline = parse2(data.get("registration_deadline"), event.registration_deadline)
  event.is_active = bool(data.get("is_active", event.is_active))
  
  new_image_url = data.get("image_url")
  if new_image_url is not None:
    event.image_url = new_image_url.strip() or None
  db.session.commit()
  return jsonify(event.to_dict())


@admin_bp.post("/events/<int:event_id>/image")
@jwt_required()
def admin_events_upload_image(event_id: int):
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403

  event = Event.query.get_or_404(event_id)
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
  
  # Optimize the image
  optimize_success, optimize_msg = process_uploaded_image(path, max_width=1920, max_height=1080, quality=85)
  if optimize_success:
    print(f"Image optimized: {optimize_msg}")
  
  event.image_url = f"/uploads/{filename}"
  db.session.commit()
  return jsonify({"image_url": event.image_url})


@admin_bp.delete("/events/<int:event_id>")
@jwt_required()
def admin_events_delete(event_id: int):
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403
  event = Event.query.get_or_404(event_id)
  
  # Delete associated enrollments first (cascade delete)
  EventEnrollment.query.filter_by(event_id=event_id).delete()
  
  db.session.delete(event)
  db.session.commit()
  return jsonify({"message": "Eliminado"})


@admin_bp.get("/events/<int:event_id>/enrollments")
@jwt_required()
def admin_events_enrollments(event_id: int):
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user or user.role != "admin":
    return jsonify({"message":"Forbidden"}), 403
  event = Event.query.get_or_404(event_id)
  enrollments = EventEnrollment.query.filter_by(event_id=event_id).order_by(EventEnrollment.enrollment_date.desc()).all()
  return jsonify({
    "event": event.to_dict(),
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
    "initial_password": u.initial_password,  # Always return initial password for admin display
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
  password = (data.get("password") or "").strip()
  membership_type = data.get("membership_type") or "normal"

  if not email or not name:
    return jsonify({"message": "Email y nombre son requeridos"}), 400
  if User.query.filter_by(email=email).first():
    return jsonify({"message": "Email ya existe"}), 400

  if not password:
    next_id = (db.session.query(func.max(User.id)).scalar() or 0) + 1
    password = f"slacc{next_id:03d}"

  from werkzeug.security import generate_password_hash
  new_member = User()
  new_member.email = email
  new_member.name = name
  new_member.password_hash = generate_password_hash(password)
  new_member.initial_password = password
  new_member.role = "member"
  new_member.membership_type = membership_type
  new_member.is_active = True
  new_member.payment_status = data.get("payment_status") or "due"
  db.session.add(new_member)
  db.session.commit()

  # TODO: Send credentials via secure email
  resp = new_member.to_safe_dict()
  resp.update({
    "message": "Socio creado. Credenciales deben ser enviadas por email.",
    "initial_password": new_member.initial_password,
  })
  return jsonify(resp), 201

