from flask import Blueprint, jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from ..extensions import db
from sqlalchemy import or_
from ..models.event import Event, EventEnrollment
from ..models.user import User
from datetime import datetime, timezone

events_bp = Blueprint("events", __name__, url_prefix="/api")


@events_bp.get("/events")
def list_events():
    event_type = (request.args.get("type") or "").strip().lower()
    past = (request.args.get("past") or "").strip().lower() in ("1", "true", "yes")

    now = datetime.now(timezone.utc)
    q = Event.query
    if event_type in ("webinar", "presencial"):
        q = q.filter(Event.format == event_type)

    if past:
        q = q.filter(Event.start_date != None).filter(Event.start_date < now).order_by(Event.start_date.desc())
    else:
        q = q.filter(Event.is_active == True)
        q = q.filter(or_(Event.start_date == None, Event.start_date >= now))
        q = q.order_by(Event.start_date.asc())

    events = q.all()
    
    # Check if user is authenticated to include enrollment status
    user_email = None
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
        if uid:
            u = User.query.get(int(uid))
            if u:
                user_email = u.email
    except Exception:
        pass
    
    result = []
    for e in events:
        data = e.to_dict()
        # métricas de cupos
        enrolled_count = EventEnrollment.query.filter_by(event_id=e.id).filter(EventEnrollment.payment_status != "cancelled").count()
        data["enrolled_count"] = enrolled_count
        data["seats_left"] = max(0, (e.max_students or 0) - enrolled_count) if e.max_students else None
        
        # Check if current user is enrolled
        data["is_enrolled"] = False
        if user_email:
            enrollment = EventEnrollment.query.filter_by(
                event_id=e.id,
                student_email=user_email
            ).first()
            data["is_enrolled"] = enrollment is not None
        
        result.append(data)
    return jsonify(result)


@events_bp.get("/events/<int:event_id>")
def event_detail(event_id: int):
    event = Event.query.get_or_404(event_id)
    data = event.to_dict()

    # Precio para el usuario actual (si hay token)
    price_for_user = event.price_non_member
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
        if uid:
            u = User.query.get(int(uid))
            if u and u.role == "member" and u.is_active and u.payment_status == "paid":
                price_for_user = event.get_price_for_membership_type(u.membership_type, is_member=True)
    except Exception:
        pass

    data["price_for_user"] = price_for_user
    # Cupo restante
    enrolled_count = EventEnrollment.query.filter_by(event_id=event.id).filter(EventEnrollment.payment_status != "cancelled").count()
    data["enrolled_count"] = enrolled_count
    data["seats_left"] = max(0, (event.max_students or 0) - enrolled_count) if event.max_students else None
    
    # Check if current user is enrolled
    data["is_enrolled"] = False
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
        if uid:
            u = User.query.get(int(uid))
            if u:
                enrollment = EventEnrollment.query.filter_by(
                    event_id=event.id,
                    student_email=u.email
                ).first()
                data["is_enrolled"] = enrollment is not None
    except Exception:
        pass
    
    return jsonify(data)


@events_bp.post("/events/<int:event_id>/enroll")
def enroll_event(event_id: int):
    event = Event.query.get_or_404(event_id)

    if not event.is_active:
        return jsonify({"error": "El evento no está activo"}), 400
    if event.registration_deadline and datetime.now() > event.registration_deadline:
        return jsonify({"error": "El plazo de inscripción terminó"}), 400

    # Capacidad
    enrolled_count = EventEnrollment.query.filter_by(event_id=event.id).filter(EventEnrollment.payment_status != "cancelled").count()
    if event.max_students and enrolled_count >= event.max_students:
        return jsonify({"error": "Cupos completos"}), 400

    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    if not name or not email:
        return jsonify({"error": "Nombre y email son requeridos"}), 400

    # Check for existing enrollment
    existing_enrollment = EventEnrollment.query.filter_by(
        event_id=event.id,
        student_email=email
    ).first()
    
    if existing_enrollment:
        return jsonify({"error": "Ya estás inscrito en este evento"}), 400

    # Determinar precio según usuario actual
    user_id = None
    is_member = False
    membership_type = None
    payment_amount = event.price_non_member
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
        if uid:
            u = User.query.get(int(uid))
            if u and u.is_active:
                user_id = u.id
                # Admins and paid members get member pricing
                if (u.role == "admin") or (u.role == "member" and u.payment_status == "paid"):
                    is_member = True
                    membership_type = u.membership_type
                    payment_amount = event.get_price_for_membership_type(membership_type, is_member=True)
    except Exception:
        pass

    enrollment = EventEnrollment()
    enrollment.event_id = event.id
    enrollment.user_id = user_id
    enrollment.student_name = name
    enrollment.student_email = email
    enrollment.student_phone = phone
    enrollment.payment_status = "pending"
    enrollment.payment_amount = payment_amount
    enrollment.membership_type = membership_type
    enrollment.is_member = is_member
    db.session.add(enrollment)
    db.session.commit()

    return jsonify({
        "message": "Inscripción registrada",
        "enrollment": enrollment.to_dict()
    }), 201


