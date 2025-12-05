from datetime import datetime
from ..extensions import db


class Application(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  # Información Personal
  name = db.Column(db.String(255), nullable=False)
  email = db.Column(db.String(255), nullable=False)
  website = db.Column(db.String(255))
  city = db.Column(db.String(100))
  country = db.Column(db.String(100))
  whatsapp = db.Column(db.String(50))
  
  # Información Académica
  specialization = db.Column(db.String(255))
  residency_end_date = db.Column(db.Date)
  university = db.Column(db.String(255))
  fellowship_date = db.Column(db.Date)
  fellowship_location = db.Column(db.String(255))
  
  # Información Profesional
  current_hospital = db.Column(db.String(255))
  current_position = db.Column(db.String(255))
  teaching_degree = db.Column(db.String(100))
  
  # Legacy fields
  phone = db.Column(db.String(50))
  motivation = db.Column(db.Text)
  experience_years = db.Column(db.Integer)
  
  # System fields
  membership_type = db.Column(db.String(20), default="normal")
  status = db.Column(db.String(20), default="pending")
  resolution_note = db.Column(db.Text)
  decided_at = db.Column(db.DateTime)
  created_at = db.Column(db.DateTime, default=datetime.utcnow)
  
  # Relationships
  attachments = db.relationship("ApplicationAttachment", backref="application", lazy=True, cascade="all, delete-orphan")
  
  def to_dict(self):
    return {
      "id": self.id,
      "name": self.name,
      "email": self.email,
      "website": self.website,
      "city": self.city,
      "country": self.country,
      "whatsapp": self.whatsapp,
      "specialization": self.specialization,
      "residency_end_date": self.residency_end_date.isoformat() if self.residency_end_date else None,
      "university": self.university,
      "fellowship_date": self.fellowship_date.isoformat() if self.fellowship_date else None,
      "fellowship_location": self.fellowship_location,
      "current_hospital": self.current_hospital,
      "current_position": self.current_position,
      "teaching_degree": self.teaching_degree,
      "phone": self.phone,
      "motivation": self.motivation,
      "experience_years": self.experience_years,
      "membership_type": self.membership_type,
      "status": self.status,
      "resolution_note": self.resolution_note,
      "decided_at": self.decided_at.isoformat() if self.decided_at else None,
      "created_at": self.created_at.isoformat() if self.created_at else None,
      "attachments": [{"id": att.id, "file_url": att.file_url} for att in self.attachments],
    }


class ApplicationAttachment(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  application_id = db.Column(db.Integer, db.ForeignKey("application.id"), nullable=False)
  file_url = db.Column(db.String(500))
  created_at = db.Column(db.DateTime, default=datetime.utcnow)

