"""File upload validation utilities for secure file handling"""
import os

# Allowed file extensions
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx'}
ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mpeg'}

# File size limits (in bytes)
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_DOCUMENT_SIZE = 20 * 1024 * 1024  # 20MB
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB

# Image magic numbers (file signatures)
IMAGE_SIGNATURES = {
    b'\xFF\xD8\xFF': 'jpeg',  # JPEG
    b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A': 'png',  # PNG
    b'\x47\x49\x46\x38': 'gif',  # GIF
    b'\x52\x49\x46\x46': 'webp'  # RIFF (WebP container)
}


def validate_file_extension(filename, allowed_extensions):
    """
    Validate file extension.
    
    Args:
        filename: Name of the file
        allowed_extensions: Set of allowed extensions
        
    Returns:
        bool: True if extension is allowed
    """
    if not filename:
        return False
    ext = os.path.splitext(filename)[1].lower()
    return ext in allowed_extensions


def detect_image_type(file_path):
    """Detect image type by reading file signature (magic numbers)"""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(12)
            for signature, img_type in IMAGE_SIGNATURES.items():
                if header.startswith(signature):
                    return img_type
        return None
    except Exception:
        return None


def validate_image(file_path):
    """Validate image file using extension and file signature"""
    try:
        file_size = os.path.getsize(file_path)
        if file_size > MAX_IMAGE_SIZE:
            return False, f"Image too large (max {MAX_IMAGE_SIZE // (1024*1024)}MB)"
        
        # Check extension
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            return False, f"Invalid image extension: {ext}"
        
        # Verify file signature
        img_type = detect_image_type(file_path)
        if not img_type:
            return False, "File is not a valid image"
        
        return True, f"image/{img_type}"
    except Exception as e:
        return False, f"Error validating image: {str(e)}"


def validate_document(file_path):
    """Validate document file"""
    try:
        file_size = os.path.getsize(file_path)
        if file_size > MAX_DOCUMENT_SIZE:
            return False, f"Document too large (max {MAX_DOCUMENT_SIZE // (1024*1024)}MB)"
        
        # Check extension
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
            return False, f"Invalid document extension: {ext}"
        
        # Basic validation - check if file starts with PDF magic number
        if ext == '.pdf':
            with open(file_path, 'rb') as f:
                header = f.read(4)
                if header != b'%PDF':
                    return False, "File is not a valid PDF"
        
        return True, f"application/{ext[1:]}"
    except Exception as e:
        return False, f"Error validating document: {str(e)}"


def validate_video(file_path):
    """Validate video file"""
    try:
        file_size = os.path.getsize(file_path)
        if file_size > MAX_VIDEO_SIZE:
            return False, f"Video too large (max {MAX_VIDEO_SIZE // (1024*1024)}MB)"
        
        # Check extension
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in ALLOWED_VIDEO_EXTENSIONS:
            return False, f"Invalid video extension: {ext}"
        
        return True, f"video/{ext[1:]}"
    except Exception as e:
        return False, f"Error validating video: {str(e)}"


def get_safe_filename(original_filename):
    """Generate a safe, unique filename"""
    import uuid
    ext = os.path.splitext(original_filename)[1].lower()
    # Only allow specific extensions
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf', '.doc', '.docx', '.mp4', '.mov', '.avi'}
    if ext not in allowed_extensions:
        ext = '.bin'
    return f"{uuid.uuid4().hex}{ext}"
