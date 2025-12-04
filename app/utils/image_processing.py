"""
Image processing utilities for optimizing uploaded images.
"""
import os
from PIL import Image
from io import BytesIO


def optimize_image(image_path, max_width=1920, max_height=1080, quality=85):
    """
    Optimize an image by resizing and compressing it.
    
    Args:
        image_path: Path to the image file
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels
        quality: JPEG quality (1-100, higher is better)
    
    Returns:
        bool: True if optimization succeeded, False otherwise
    """
    try:
        with Image.open(image_path) as img:
            # Convert RGBA to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if image is larger than max dimensions
            if img.width > max_width or img.height > max_height:
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # Save optimized image
            img.save(image_path, 'JPEG', quality=quality, optimize=True)
            return True
    except Exception as e:
        print(f"Error optimizing image: {e}")
        return False


def process_uploaded_image(file_path, max_width=1920, max_height=1080, quality=85):
    """
    Process an uploaded image file by optimizing it.
    
    Args:
        file_path: Path to the uploaded image
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels
        quality: JPEG quality (1-100)
    
    Returns:
        tuple: (success: bool, message: str)
    """
    if not os.path.exists(file_path):
        return False, "File not found"
    
    # Get file size before optimization
    size_before = os.path.getsize(file_path)
    
    # Optimize the image
    success = optimize_image(file_path, max_width, max_height, quality)
    
    if not success:
        return False, "Failed to optimize image"
    
    # Get file size after optimization
    size_after = os.path.getsize(file_path)
    reduction = ((size_before - size_after) / size_before) * 100 if size_before > 0 else 0
    
    return True, f"Image optimized (reduced by {reduction:.1f}%)"
