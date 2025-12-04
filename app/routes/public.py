import os
import uuid
from flask import Blueprint, jsonify, request, current_app
import requests
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models.news import News
from ..models.application import Application
from ..utils.file_validation import validate_image, validate_document, get_safe_filename
from ..utils.image_processing import process_uploaded_image

public_bp = Blueprint("public", __name__, url_prefix="/api")


@public_bp.post("/applications")
def create_application():
  # Acepta JSON (legacy) o multipart/form-data con PDF
  if request.content_type and request.content_type.startswith('multipart/form-data'):
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    phone = (request.form.get("phone") or "").strip()
    motivation = (request.form.get("motivation") or "").strip()
    specialization = (request.form.get("specialization") or "").strip()
    experience = request.form.get("experience")
    app_row = Application()
    app_row.name = name
    app_row.email = email
    app_row.phone = phone
    app_row.motivation = motivation
    app_row.specialization = specialization
    app_row.experience_years = experience
    db.session.add(app_row)
    db.session.flush()

    if "document" in request.files and request.files["document"]:
      f = request.files["document"]
      if f.filename and f.filename.lower().endswith(".pdf"):
        namef = get_safe_filename(f.filename)
        upload_dir = os.path.abspath(current_app.config["UPLOAD_DIR"]) 
        path = os.path.join(upload_dir, namef)
        f.save(path)
        
        # Validate file type after saving
        is_valid, result = validate_document(path)
        if not is_valid:
          os.remove(path)  # Delete invalid file
          return jsonify({"error": f"Archivo inválido: {result}"}), 400
        
        from ..models.application import ApplicationAttachment
        att = ApplicationAttachment()
        att.application_id = app_row.id
        att.file_url = f"/uploads/{namef}"
        db.session.add(att)

    db.session.commit()
    return jsonify({"id": app_row.id, "status": app_row.status}), 201
  else:
    data = request.get_json() or {}
    app_row = Application()
    app_row.name = data.get("name", "").strip()
    app_row.email = (data.get("email", "").strip().lower())
    app_row.phone = data.get("phone", "").strip()
    app_row.motivation = data.get("motivation", "").strip()
    app_row.specialization = data.get("specialization", "").strip()
    app_row.experience_years = data.get("experience")
    db.session.add(app_row)
    db.session.commit()
    return jsonify({"id": app_row.id, "status": app_row.status}), 201


@public_bp.get("/news")
def news_list():
  from ..models.user import User
  q = News.query.filter_by(status="published")
  category = (request.args.get("category") or "").strip().lower()
  if category in ("comunicados", "prensa", "blog"):
    q = q.filter(News.category == category)
  items = q.order_by(News.order_index.asc(), News.created_at.desc()).all()
  
  result = []
  for n in items:
    author_name = None
    if n.created_by_user_id:
      user = User.query.get(n.created_by_user_id)
      if user:
        author_name = user.name
    
    result.append({
      "id": n.id,
      "title": n.title,
      "excerpt": n.excerpt,
      "image_url": n.image_url,
      "category": n.category,
      "created_at": n.created_at.isoformat() if n.created_at else None,
      "author_name": author_name
    })
  
  return jsonify(result)


@public_bp.get("/news/<int:news_id>")
def news_detail(news_id):
    """Obtener una noticia específica por ID"""
    from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
    from app.models.user import User
    
    news = News.query.get(news_id)
    if not news:
        return jsonify({"error": "Noticia no encontrada"}), 404
    
    # Intentar verificar JWT (opcional - no falla si no hay token)
    is_admin = False
    try:
        verify_jwt_in_request(optional=True)
        current_user_id = get_jwt_identity()
        if current_user_id:
            user = User.query.get(int(current_user_id))
            if user and user.role == "admin":
                is_admin = True
    except Exception as e:
        # Si hay error verificando JWT, continuar como usuario no autenticado
        print(f"JWT verification failed: {e}")
    
    # Admin puede ver cualquier noticia
    if is_admin:
        return jsonify(news.to_dict())
    
    # Usuario no autenticado o no admin solo puede ver noticias publicadas
    if news.status != "published":
        return jsonify({"error": "Noticia no encontrada"}), 404
    
    return jsonify(news.to_dict())


@public_bp.get("/instagram/recent")
def instagram_recent():
    """Devuelve últimos 3 posts de Instagram vía Graph API. Usa placeholders si no hay credenciales."""
    INSTAGRAM_PERMALINK = "https://instagram.com/slacc_cadera"
    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    user_id = os.environ.get("INSTAGRAM_USER_ID")
    limit = int(request.args.get("limit", 3))

    # Check if credentials are actually valid (not just "..." placeholder)
    if not access_token or not user_id or access_token == "..." or user_id == "...":
        # Fallback placeholder
        placeholder = [
            {
                "id": "ph1",
                "caption": "Caso clínico de artroplastia – discusión multidisciplinaria",
                "media_url": "https://images.unsplash.com/photo-1544717302-de2939b7ef71?q=80&w=800&auto=format&fit=crop",
                "permalink": INSTAGRAM_PERMALINK
            },
            {
                "id": "ph2",
                "caption": "Tips quirúrgicos: abordajes en cadera compleja",
                "media_url": "https://images.unsplash.com/photo-1550831107-1553da8c8464?q=80&w=800&auto=format&fit=crop",
                "permalink": INSTAGRAM_PERMALINK
            },
            {
                "id": "ph3",
                "caption": "Agenda: próximos webinars y cursos SLACC",
                "media_url": "https://images.unsplash.com/photo-1526256262350-7da7584cf5eb?q=80&w=800&auto=format&fit=crop",
                "permalink": INSTAGRAM_PERMALINK
            },
        ]
        return jsonify(placeholder[:limit])

    try:
        url = (
            f"https://graph.instagram.com/{user_id}/media"
            f"?fields=id,caption,media_url,permalink,media_type"
            f"&limit={limit}"
            f"&access_token={access_token}"
        )
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        # Filtrar sólo imágenes/video con media_url
        cleaned = [
            {
                "id": d.get("id"),
                "caption": d.get("caption"),
                "media_url": d.get("media_url"),
                "permalink": d.get("permalink"),
            }
            for d in data if d.get("media_url")
        ]
        return jsonify(cleaned)
    except Exception as e:
        current_app.logger.error(f"Instagram error: {e}")
        return jsonify({"error": "instagram_fetch_failed"}), 502

@public_bp.post("/news")
@jwt_required()
def news_create():
  try:
    uid = int(get_jwt_identity())
    print(f"Creating news for user {uid}")
    
    # multipart/form-data
    title = (request.form.get("title") or "").strip()
    excerpt = (request.form.get("excerpt") or "").strip()
    content = (request.form.get("content") or "").strip()
    image_url = None
    
    print(f"Form data: title={title}, excerpt={excerpt}, content={content[:50]}...")
    print(f"Files: {list(request.files.keys())}")
    
    if "image" in request.files and request.files["image"]:
      f = request.files["image"]
      if f.filename:
        name = get_safe_filename(f.filename)
        upload_dir = os.path.abspath(current_app.config["UPLOAD_DIR"]) 
        path = os.path.join(upload_dir, name)
        print(f"Saving image to {path}")
        f.save(path)
        
        # Validate file type after saving
        is_valid, result = validate_image(path)
        if not is_valid:
          os.remove(path)  # Delete invalid file
          return jsonify({"error": f"Imagen inválida: {result}"}), 400
        
        # Optimize the image
        optimize_success, optimize_msg = process_uploaded_image(path, max_width=1920, max_height=1080, quality=85)
        if optimize_success:
          print(f"Image optimized: {optimize_msg}")
        
        image_url = f"/uploads/{name}"
    
    if not image_url:
      image_url = "https://images.unsplash.com/photo-1532012197267-da84d127e765?auto=format&fit=crop&w=1400&q=60"
    
    print(f"Final image_url: {image_url}")
    
    n = News()
    n.title = title
    n.excerpt = excerpt
    n.content = content
    n.image_url = image_url
    n.category = (request.form.get("category") or "comunicados").strip().lower()
    n.status = "pending"
    n.created_by_user_id = uid
    db.session.add(n)
    db.session.commit()
    print(f"News created with ID {n.id}")
    return jsonify({"id": n.id, "status": n.status}), 201
    
  except Exception as e:
    print(f"Error creating news: {e}")
    return jsonify({"error": str(e)}), 500


