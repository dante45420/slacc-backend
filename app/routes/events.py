from flask import Blueprint, jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from ..extensions import db
from sqlalchemy import or_
from ..models.course import Course, CourseEnrollment
from ..models.user import User
from datetime import datetime, timezone

events_bp = Blueprint("events", __name__, url_prefix="/api")


@events_bp.get("/events")
def list_events():
    event_type = (request.args.get("type") or "").strip().lower()
    past = (request.args.get("past") or "").strip().lower() in ("1", "true", "yes")

    now = datetime.now(timezone.utc)
    q = Course.query
    if event_type in ("webinar", "presencial"):
        q = q.filter(Course.format == event_type)

    if past:
        q = q.filter(Course.start_date != None).filter(Course.start_date < now).order_by(Course.start_date.desc())
    else:
        q = q.filter(Course.is_active == True)
        q = q.filter(or_(Course.start_date == None, Course.start_date >= now))
        q = q.order_by(Course.start_date.asc())

    courses = q.all()
    result = []
    for c in courses:
        data = c.to_dict()
        # métricas de cupos
        enrolled_count = CourseEnrollment.query.filter_by(course_id=c.id).filter(CourseEnrollment.payment_status != "cancelled").count()
        data["enrolled_count"] = enrolled_count
        data["seats_left"] = max(0, (c.max_students or 0) - enrolled_count) if c.max_students else None
        result.append(data)
    return jsonify(result)


@events_bp.get("/events/<int:course_id>")
def event_detail(course_id: int):
    course = Course.query.get_or_404(course_id)
    data = course.to_dict()

    # Precio para el usuario actual (si hay token)
    price_for_user = course.price_non_member
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
        if uid:
            u = User.query.get(int(uid))
            if u and u.role == "member" and u.is_active and u.payment_status == "paid":
                price_for_user = course.get_price_for_membership_type(u.membership_type, is_member=True)
    except Exception:
        pass

    data["price_for_user"] = price_for_user
    # Cupo restante
    enrolled_count = CourseEnrollment.query.filter_by(course_id=course.id).filter(CourseEnrollment.payment_status != "cancelled").count()
    data["enrolled_count"] = enrolled_count
    data["seats_left"] = max(0, (course.max_students or 0) - enrolled_count) if course.max_students else None
    
    # Check if current user is enrolled
    data["is_enrolled"] = False
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
        if uid:
            u = User.query.get(int(uid))
            if u:
                enrollment = CourseEnrollment.query.filter_by(
                    course_id=course.id,
                    student_email=u.email
                ).first()
                data["is_enrolled"] = enrollment is not None
    except Exception:
        pass
    
    return jsonify(data)


@events_bp.post("/events/<int:course_id>/enroll")
def enroll_event(course_id: int):
    course = Course.query.get_or_404(course_id)

    if not course.is_active:
        return jsonify({"error": "El evento no está activo"}), 400
    if course.registration_deadline and datetime.now() > course.registration_deadline:
        return jsonify({"error": "El plazo de inscripción terminó"}), 400

    # Capacidad
    enrolled_count = CourseEnrollment.query.filter_by(course_id=course.id).filter(CourseEnrollment.payment_status != "cancelled").count()
    if course.max_students and enrolled_count >= course.max_students:
        return jsonify({"error": "Cupos completos"}), 400

    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    if not name or not email:
        return jsonify({"error": "Nombre y email son requeridos"}), 400

    # Check for existing enrollment
    existing_enrollment = CourseEnrollment.query.filter_by(
        course_id=course.id,
        student_email=email
    ).first()
    
    if existing_enrollment:
        return jsonify({"error": "Ya estás inscrito en este evento"}), 400

    # Determinar precio según usuario actual
    user_id = None
    is_member = False
    membership_type = None
    payment_amount = course.price_non_member
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
                    payment_amount = course.get_price_for_membership_type(membership_type, is_member=True)
    except Exception:
        pass

    enrollment = CourseEnrollment()
    enrollment.course_id = course.id
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


