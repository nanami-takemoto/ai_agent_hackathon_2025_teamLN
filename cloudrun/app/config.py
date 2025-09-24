"""アプリケーション設定"""
import os

class Config:
    """アプリケーション設定クラス"""
    
    # Google Cloud設定
    PROJECT_ID = os.environ.get('PROJECT_ID')
    REGION = os.environ.get('REGION', 'asia-northeast1')
    BUCKET_NAME = os.environ.get('BUCKET_NAME')
    # Imagen用リージョン（公開モデルはus-central1優先）
    IMAGEN_REGION = os.environ.get('IMAGEN_REGION', 'us-central1')
    IMAGEN_MODEL = os.environ.get('IMAGEN_MODEL', 'imagen-3.0-generate-001')
    # SDXL Inpainting設定
    SDXL_MODEL = os.environ.get('SDXL_MODEL', 'imagegeneration@006')
    SDXL_REGION = os.environ.get('SDXL_REGION', 'us-central1')
    # 任意: Vertex AI Vision 推論用エンドポイント設定（未指定なら検出はスキップ）
    VISION_ENDPOINT_ID = os.environ.get('VISION_ENDPOINT_ID')  # 例: 1234567890123456789
    VISION_REGION = os.environ.get('VISION_REGION', REGION)
    
    # アプリケーション設定
    PORT = int(os.environ.get('PORT', 8080))
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # 画像処理設定
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
    RESIZE_LONG_SIDE = int(os.environ.get('RESIZE_LONG_SIDE', 1536))
    JPEG_QUALITY = int(os.environ.get('JPEG_QUALITY', 92))
    
    # ストレージ設定
    PROCESSED_IMAGES_PREFIX = "processed_images/"
    
    @classmethod
    def validate_config(cls):
        """設定の検証"""
        required_vars = ['PROJECT_ID', 'BUCKET_NAME']
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True
