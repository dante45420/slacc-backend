from datetime import timedelta
from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from ..extensions import db
from ..models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api")


@auth_bp.post("/auth/login")
def login():
  data = request.get_json() or {}
  email = data.get("email", "").strip().lower()
  password = data.get("password", "")
  user = User.query.filter_by(email=email).first()
  if not user or not user.check_password(password):
    return jsonify({"message": "Credenciales inválidas"}), 401
  
  # Convertir el ID a string para evitar problemas con JWT
  token = create_access_token(identity=str(user.id), expires_delta=timedelta(days=3))
  return jsonify({"access_token": token, "user": user.to_safe_dict()})


@auth_bp.get("/me")
@jwt_required()
def me():
  uid = get_jwt_identity()
  # Convertir de vuelta a int para la consulta
  user = User.query.get(int(uid))
  if not user:
    return jsonify({"message": "No encontrado"}), 404
  return jsonify(user.to_safe_dict())


@auth_bp.post("/auth/change-password")
@jwt_required()
def change_password():
  """Permite al usuario autenticado cambiar su contraseña."""
  uid = int(get_jwt_identity())
  user = User.query.get(uid)
  if not user:
    return jsonify({"message": "No encontrado"}), 404

  data = request.get_json() or {}
  current_password = data.get("current_password", "")
  new_password = data.get("new_password", "")

  if not current_password or not new_password:
    return jsonify({"message": "Faltan campos requeridos"}), 400

  if not user.check_password(current_password):
    return jsonify({"message": "La contraseña actual es incorrecta"}), 400

  if len(new_password) < 8:
    return jsonify({"message": "La nueva contraseña debe tener al menos 8 caracteres"}), 400

  user.set_password(new_password)
  # Si existía una contraseña inicial en texto plano, ya no es válida
  user.initial_password = None
  db.session.commit()
  return jsonify({"message": "Contraseña actualizada", "user": user.to_safe_dict()})


