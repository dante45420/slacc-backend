from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db


class User(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  email = db.Column(db.String(255), unique=True, nullable=False)
  name = db.Column(db.String(255), nullable=False)
  password_hash = db.Column(db.String(255), nullable=False)
  role = db.Column(db.String(20), nullable=False, default="member")  # admin | member
  membership_type = db.Column(db.String(20), default="normal")  # joven (Nex Gen) | normal | gratuito (Emérito)
  is_active = db.Column(db.Boolean, default=True)
  payment_status = db.Column(db.String(20), default="due")  # none | due | paid
  auto_payment_enabled = db.Column(db.Boolean, default=False)
  initial_password = db.Column(db.String(255), nullable=True)  # Plaintext initial password for one-time display (insecure but requested by client)
  created_at = db.Column(db.DateTime, default=datetime.utcnow)

  def set_password(self, raw):
    self.password_hash = generate_password_hash(raw)

  def check_password(self, raw):
    return check_password_hash(self.password_hash, raw)

  def to_safe_dict(self):
    return {
      "id": self.id,
      "email": self.email,
      "name": self.name,
      "role": self.role,
      "membership_type": self.membership_type,
      "is_active": self.is_active,
      "payment_status": self.payment_status,
      "auto_payment_enabled": self.auto_payment_enabled,
    }


