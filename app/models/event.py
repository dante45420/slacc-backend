from datetime import datetime
from ..extensions import db


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    content = db.Column(db.Text)  # Contenido detallado del evento
    instructor = db.Column(db.String(255))  # Instructor del evento
    duration_hours = db.Column(db.Integer)  # Duración en horas
    format = db.Column(db.String(20), default="webinar")  # webinar | presencial
    location = db.Column(db.String(255))  # Ubicación física o link para eventos presenciales/online
    max_students = db.Column(db.Integer)  # Máximo de estudiantes (opcional)
    price_member = db.Column(db.Float, nullable=False, default=0)  # Precio para socios
    price_non_member = db.Column(db.Float, nullable=False, default=0)  # Precio para no socios
    price_joven = db.Column(db.Float, default=0)  # Precio especial para socios jóvenes
    price_gratuito = db.Column(db.Float, default=0)  # Precio especial para socios gratuitos
    start_date = db.Column(db.DateTime)  # Fecha de inicio
    end_date = db.Column(db.DateTime)  # Fecha de fin
    registration_deadline = db.Column(db.DateTime)  # Fecha límite de inscripción
    is_active = db.Column(db.Boolean, default=True)  # Si el evento está activo
    image_url = db.Column(db.String(500))  # Imagen del evento
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "content": self.content,
            "instructor": self.instructor,
            "duration_hours": self.duration_hours,
            "format": self.format,
            "location": self.location,
            "max_students": self.max_students,
            "price_member": self.price_member,
            "price_non_member": self.price_non_member,
            "price_joven": self.price_joven,
            "price_gratuito": self.price_gratuito,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "registration_deadline": self.registration_deadline.isoformat() if self.registration_deadline else None,
            "is_active": self.is_active,
            "image_url": self.image_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_price_for_membership_type(self, membership_type, is_member=False):
        """Obtiene el precio según el tipo de membresía"""
        if not is_member:
            return self.price_non_member
        
        if membership_type == "joven":
            return self.price_joven if self.price_joven > 0 else self.price_member
        elif membership_type == "gratuito":
            return self.price_gratuito if self.price_gratuito > 0 else 0
        else:  # normal
            return self.price_member


class EventEnrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)  # Puede ser null para no socios
    student_name = db.Column(db.String(255), nullable=False)  # Nombre del estudiante
    student_email = db.Column(db.String(255), nullable=False)  # Email del estudiante
    student_phone = db.Column(db.String(50))  # Teléfono del estudiante
    payment_status = db.Column(db.String(20), default="pending")  # pending | paid | cancelled
    payment_amount = db.Column(db.Float, nullable=False)  # Monto pagado
    membership_type = db.Column(db.String(20))  # Tipo de membresía al momento de la inscripción
    is_member = db.Column(db.Boolean, default=False)  # Si era socio al momento de inscribirse
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_date = db.Column(db.DateTime)  # Fecha de pago confirmado

    def to_dict(self):
        return {
            "id": self.id,
            "event_id": self.event_id,
            "user_id": self.user_id,
            "student_name": self.student_name,
            "student_email": self.student_email,
            "student_phone": self.student_phone,
            "payment_status": self.payment_status,
            "payment_amount": self.payment_amount,
            "membership_type": self.membership_type,
            "is_member": self.is_member,
            "enrollment_date": self.enrollment_date.isoformat() if self.enrollment_date else None,
            "payment_date": self.payment_date.isoformat() if self.payment_date else None,
        }
