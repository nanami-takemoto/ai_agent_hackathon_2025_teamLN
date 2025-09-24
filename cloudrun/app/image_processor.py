"""画像処理サービス"""
import io
import base64
from typing import Dict, Optional
from PIL import Image
from config import Config

class ImageProcessor:
    """画像処理を管理するクラス"""
    
    @staticmethod
    def decode_base64_image(base64_data: str) -> Image.Image:
        """Base64エンコードされた画像をデコード"""
        try:
            image_data = base64.b64decode(base64_data)
            return Image.open(io.BytesIO(image_data))
        except Exception as e:
            raise Exception(f"Base64画像のデコードに失敗しました: {str(e)}")
    
    @staticmethod
    def validate_image(image: Image.Image) -> None:
        """画像の検証"""
        # 画像サイズの検証
        img_byte_arr = io.BytesIO()
        fmt = image.format if image.format else 'PNG'
        image.save(img_byte_arr, format=fmt)
        
        if len(img_byte_arr.getvalue()) > Config.MAX_IMAGE_SIZE:
            raise Exception(f"画像サイズが大きすぎます。最大{Config.MAX_IMAGE_SIZE // (1024*1024)}MBまで")
        
        # 画像形式の検証
        if image.format and image.format.lower() not in [fmt[1:] for fmt in Config.ALLOWED_IMAGE_FORMATS]:
            raise Exception(f"サポートされていない画像形式です: {image.format}")
    
    @staticmethod
    def downscale_if_needed(image: Image.Image) -> Image.Image:
        """長辺が設定値を超える場合に縮小。"""
        try:
            width, height = image.size
            long_side = max(width, height)
            target = Config.RESIZE_LONG_SIDE
            if long_side <= target:
                return image
            scale = target / float(long_side)
            new_size = (int(width * scale), int(height * scale))
            # RGB化して高品質リサンプリング
            img_rgb = image.convert('RGB') if image.mode != 'RGB' else image
            return img_rgb.resize(new_size, Image.Resampling.LANCZOS)
        except Exception:
            return image
    
    @staticmethod
    def process_image(image: Image.Image) -> Image.Image:
        """画像の基本処理（リサイズ適用）"""
        return ImageProcessor.downscale_if_needed(image)
    
    @staticmethod
    def get_image_info(image: Image.Image, source_blob: Optional[str] = None) -> Dict:
        """画像の基本情報を取得"""
        info = {
            "format": image.format,
            "mode": image.mode,
            "size": image.size,
            "width": image.width,
            "height": image.height
        }
        
        if source_blob:
            info["source_blob"] = source_blob
            
        return info
