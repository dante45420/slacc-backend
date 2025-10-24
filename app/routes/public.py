import os
import uuid
from flask import Blueprint, jsonify, request, current_app
import requests
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models.news import News
from ..models.application import Application

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
    app_row = Application(
      name=name,
      email=email,
      phone=phone,
      motivation=motivation,
      specialization=specialization,
      experience_years=experience,
    )
    db.session.add(app_row)
    db.session.flush()

    if "document" in request.files and request.files["document"]:
      f = request.files["document"]
      if f.filename and f.filename.lower().endswith(".pdf"):
        ext = os.path.splitext(f.filename)[1].lower() or ".pdf"
        namef = f"application-{uuid.uuid4().hex}{ext}"
        upload_dir = os.path.abspath(current_app.config["UPLOAD_DIR"]) 
        path = os.path.join(upload_dir, namef)
        f.save(path)
        from ..models.application import ApplicationAttachment
        att = ApplicationAttachment(application_id=app_row.id, file_url=f"/uploads/{namef}")
        db.session.add(att)

    db.session.commit()
    return jsonify({"id": app_row.id, "status": app_row.status}), 201
  else:
    data = request.get_json() or {}
    app_row = Application(
      name=data.get("name", "").strip(),
      email=(data.get("email", "").strip().lower()),
      phone=data.get("phone", "").strip(),
      motivation=data.get("motivation", "").strip(),
      specialization=data.get("specialization", "").strip(),
      experience_years=data.get("experience"),
    )
    db.session.add(app_row)
    db.session.commit()
    return jsonify({"id": app_row.id, "status": app_row.status}), 201


@public_bp.get("/news")
def news_list():
  q = News.query.filter_by(status="published")
  category = (request.args.get("category") or "").strip().lower()
  if category in ("comunicados", "prensa", "blog"):
    q = q.filter(News.category == category)
  items = q.order_by(News.order_index.asc(), News.created_at.desc()).all()
  return jsonify([
    {"id": n.id, "title": n.title, "excerpt": n.excerpt, "image_url": n.image_url, "category": n.category, "created_at": n.created_at.isoformat() if n.created_at else None}
    for n in items
  ])


@public_bp.get("/news/<int:news_id>")
def news_detail(news_id):
    """Obtener una noticia específica por ID"""
    news = News.query.get(news_id)
    if not news:
        return jsonify({"error": "Noticia no encontrada"}), 404
    
    # Solo noticias publicadas son visibles públicamente
    # Pero si hay un token válido de admin, puede ver cualquier noticia
    from flask_jwt_extended import get_jwt_identity, jwt_required, get_jwt
    from app.models.user import User
    
    try:
        # Intentar obtener el usuario del token
        current_user_id = get_jwt_identity()
        if current_user_id:
            user = User.query.get(int(current_user_id))
            if user and user.role == "admin":
                # Admin puede ver cualquier noticia
                return jsonify(news.to_dict())
    except:
        pass
    
    # Usuario no autenticado o no admin solo puede ver noticias publicadas
    if news.status != "published":
        return jsonify({"error": "Noticia no encontrada"}), 404
    
    return jsonify(news.to_dict())


@public_bp.get("/instagram/recent")
def instagram_recent():
    """Devuelve últimos 3 posts de Instagram vía Graph API. Usa placeholders si no hay credenciales."""
    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    user_id = os.environ.get("INSTAGRAM_USER_ID")
    limit = int(request.args.get("limit", 3))

    if not access_token or not user_id:
        # Fallback placeholder
        placeholder = [
            {
                "id": "ph1",
                "caption": "Caso clínico de artroplastia – discusión multidisciplinaria",
                "media_url": "https://images.unsplash.com/photo-1544717302-de2939b7ef71?q=80&w=800&auto=format&fit=crop",
                "permalink": "https://instagram.com/slacc_cadera"
            },
            {
                "id": "ph2",
                "caption": "Tips quirúrgicos: abordajes en cadera compleja",
                "media_url": "https://images.unsplash.com/photo-1550831107-1553da8c8464?q=80&w=800&auto=format&fit=crop",
                "permalink": "https://instagram.com/slacc_cadera"
            },
            {
                "id": "ph3",
                "caption": "Agenda: próximos webinars y cursos SLACC",
                "media_url": "https://images.unsplash.com/photo-1526256262350-7da7584cf5eb?q=80&w=800&auto=format&fit=crop",
                "permalink": "https://instagram.com/slacc_cadera"
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
        ext = os.path.splitext(f.filename)[1].lower() or ".jpg"
        name = f"news-{uuid.uuid4().hex}{ext}"
        upload_dir = os.path.abspath(current_app.config["UPLOAD_DIR"]) 
        path = os.path.join(upload_dir, name)
        print(f"Saving image to {path}")
        f.save(path)
        image_url = f"/uploads/{name}"
    
    if not image_url:
      image_url = "https://images.unsplash.com/photo-1532012197267-da84d127e765?auto=format&fit=crop&w=1400&q=60"
    
    print(f"Final image_url: {image_url}")
    
    n = News(
      title=title,
      excerpt=excerpt,
      content=content,
      image_url=image_url,
      category=(request.form.get("category") or "comunicados").strip().lower(),
      status="pending",
      created_by_user_id=uid,
    )
    db.session.add(n)
    db.session.commit()
    print(f"News created with ID {n.id}")
    return jsonify({"id": n.id, "status": n.status}), 201
    
  except Exception as e:
    print(f"Error creating news: {e}")
    return jsonify({"error": str(e)}), 500


