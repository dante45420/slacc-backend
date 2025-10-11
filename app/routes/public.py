import os
import uuid
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models.news import News
from ..models.application import Application

public_bp = Blueprint("public", __name__, url_prefix="/api")


@public_bp.post("/applications")
def create_application():
  data = request.get_json() or {}
  app_row = Application(
    name=data.get("name", "").strip(),
    email=(data.get("email", "").strip().lower()),
    phone=data.get("phone", "").strip(),
    motivation=data.get("motivation", "").strip(),
    specialization=data.get("specialization", "").strip(),
    experience_years=data.get("experience"),
    # membership_type se asigna por defecto como "normal", el admin lo cambia después
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


