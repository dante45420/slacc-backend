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


