"""이미지 처리 유틸리티"""
import base64
from io import BytesIO
from PIL import Image
from fastapi import UploadFile, File


async def image_to_base64(file: UploadFile = File(None)) -> str:
    """
    업로드된 이미지를 Base64로 인코딩
    
    Args:
        file: FastAPI UploadFile 객체
    
    Returns:
        Base64 인코딩된 이미지 문자열
    """
    if not file:
        return None
        
    try:
        # 이미지 읽기
        img = Image.open(BytesIO(await file.read()))
        
        # 최대 크기 제한 (Gemini API 제한 고려)
        max_size = 3072  # Gemini는 최대 3072x3072 지원
        if img.width > max_size or img.height > max_size:
            scale = min(max_size / img.width, max_size / img.height)
            img = img.resize((int(img.width * scale), int(img.height * scale)))
        
        # WebP 형식으로 변환 (용량 최적화)
        buffered = BytesIO()
        img.save(buffered, format="WEBP", quality=85)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        return img_str
        
    except Exception as e:
        print(f"❌ 이미지 처리 오류: {str(e)}")
        return None


def validate_image_file(file: UploadFile) -> bool:
    """
    이미지 파일 유효성 검증
    
    Args:
        file: FastAPI UploadFile 객체
    
    Returns:
        유효하면 True
    """
    if not file:
        return False
        
    # 지원되는 이미지 확장자
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
    file_ext = file.filename.lower().split('.')[-1]
    
    return f".{file_ext}" in allowed_extensions
