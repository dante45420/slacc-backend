from datetime import datetime
from ..extensions import db


class Application(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(255), nullable=False)
  email = db.Column(db.String(255), nullable=False)
  phone = db.Column(db.String(50))
  motivation = db.Column(db.Text)
  specialization = db.Column(db.String(255))  # Nueva: especialización
  experience_years = db.Column(db.Integer)    # Nueva: años de experiencia
  membership_type = db.Column(db.String(20), default="normal")  # Nueva: joven | normal | gratuito
  status = db.Column(db.String(20), default="pending")  # pending | approved | rejected | payment_pending | paid
  resolution_note = db.Column(db.Text)
  decided_at = db.Column(db.DateTime)
  created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ApplicationAttachment(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  application_id = db.Column(db.Integer, db.ForeignKey("application.id"), nullable=False)
  file_url = db.Column(db.String(500))
  created_at = db.Column(db.DateTime, default=datetime.utcnow)

