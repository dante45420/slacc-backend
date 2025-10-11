import os
import uuid
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models.course import Course, CourseEnrollment
from ..models.user import User

courses_bp = Blueprint("courses", __name__, url_prefix="/api")


@courses_bp.get("/courses")
def list_courses():
    """Listar cursos activos disponibles para inscripción"""
    courses = Course.query.filter_by(is_active=True).order_by(Course.start_date.asc()).all()
    return jsonify([course.to_dict() for course in courses])


@courses_bp.get("/courses/<int:course_id>")
def get_course(course_id):
    """Obtener detalles de un curso específico"""
    course = Course.query.get_or_404(course_id)
    return jsonify(course.to_dict())


@courses_bp.post("/courses/<int:course_id>/enroll")
def enroll_course(course_id):
    """Inscribirse a un curso (simulación de pago)"""
    course = Course.query.get_or_404(course_id)
    
    if not course.is_active:
        return jsonify({"error": "El curso no está disponible"}), 400
    
    data = request.get_json() or {}
    student_name = data.get("student_name", "").strip()
    student_email = data.get("student_email", "").strip().lower()
    student_phone = data.get("student_phone", "").strip()
    
    if not student_name or not student_email:
        return jsonify({"error": "Nombre y email son requeridos"}), 400
    
    # Verificar si el email ya está inscrito en este curso
    existing_enrollment = CourseEnrollment.query.filter_by(
        course_id=course_id, 
        student_email=student_email
    ).first()
    
    if existing_enrollment:
        return jsonify({"error": "Ya estás inscrito en este curso"}), 400
    
    # Verificar límite de estudiantes
    current_enrollments = CourseEnrollment.query.filter_by(
        course_id=course_id, 
        payment_status="paid"
    ).count()
    
    if course.max_students and current_enrollments >= course.max_students:
        return jsonify({"error": "El curso ha alcanzado su límite de estudiantes"}), 400
    
    # Verificar fecha límite de inscripción
    if course.registration_deadline and datetime.utcnow() > course.registration_deadline:
        return jsonify({"error": "La fecha límite de inscripción ha pasado"}), 400
    
    # Determinar si es socio y tipo de membresía
    user = User.query.filter_by(email=student_email).first()
    is_member = user is not None and user.is_active
    membership_type = user.membership_type if user else None
    
    # Calcular precio
    price = course.get_price_for_membership_type(membership_type, is_member)
    
    # Crear inscripción
    enrollment = CourseEnrollment(
        course_id=course_id,
        user_id=user.id if user else None,
        student_name=student_name,
        student_email=student_email,
        student_phone=student_phone,
        payment_amount=price,
        membership_type=membership_type,
        is_member=is_member,
        payment_status="pending"
    )
    
    db.session.add(enrollment)
    db.session.commit()
    
    return jsonify({
        "enrollment_id": enrollment.id,
        "course_title": course.title,
        "price": price,
        "is_member": is_member,
        "membership_type": membership_type,
        "message": "Inscripción creada. Procede al pago."
    })


@courses_bp.post("/courses/<int:course_id>/enrollments/<int:enrollment_id>/confirm-payment")
def confirm_course_payment(course_id, enrollment_id):
    """Confirmar pago de inscripción a curso (simulación)"""
    enrollment = CourseEnrollment.query.filter_by(
        id=enrollment_id, 
        course_id=course_id
    ).first_or_404()
    
    if enrollment.payment_status != "pending":
        return jsonify({"error": "La inscripción ya fue procesada"}), 400
    
    # Simular confirmación de pago
    enrollment.payment_status = "paid"
    enrollment.payment_date = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        "message": "Pago confirmado exitosamente",
        "enrollment": enrollment.to_dict()
    })


@courses_bp.get("/courses/<int:course_id>/enrollments")
@jwt_required()
def get_course_enrollments(course_id):
    """Obtener inscripciones de un curso (solo admin)"""
    uid = int(get_jwt_identity())
    user = User.query.get(uid)
    if not user or user.role != "admin":
        return jsonify({"message": "Forbidden"}), 403
    
    course = Course.query.get_or_404(course_id)
    enrollments = CourseEnrollment.query.filter_by(course_id=course_id).order_by(
        CourseEnrollment.enrollment_date.desc()
    ).all()
    
    return jsonify({
        "course": course.to_dict(),
        "enrollments": [enrollment.to_dict() for enrollment in enrollments]
    })


@courses_bp.get("/my-enrollments")
@jwt_required()
def get_my_enrollments():
    """Obtener mis inscripciones a cursos"""
    uid = int(get_jwt_identity())
    user = User.query.get(uid)
    if not user:
        return jsonify({"message": "Usuario no encontrado"}), 404
    
    enrollments = CourseEnrollment.query.filter_by(
        user_id=user.id
    ).order_by(CourseEnrollment.enrollment_date.desc()).all()
    
    # Incluir información del curso
    result = []
    for enrollment in enrollments:
        course = Course.query.get(enrollment.course_id)
        enrollment_data = enrollment.to_dict()
        enrollment_data["course"] = course.to_dict() if course else None
        result.append(enrollment_data)
    
    return jsonify(result)
