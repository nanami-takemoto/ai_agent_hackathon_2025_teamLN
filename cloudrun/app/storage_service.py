"""Cloud Storage操作サービス"""
import io
import base64
from datetime import timedelta
from typing import List, Dict, Optional
from google.cloud import storage
from PIL import Image
from config import Config

class StorageService:
    """Cloud Storage操作を管理するクラス"""
    
    def __init__(self):
        """ストレージサービスの初期化"""
        self.client = storage.Client(project=Config.PROJECT_ID)
        self.bucket = self.client.bucket(Config.BUCKET_NAME)
    
    def upload_image(self, image: Image.Image, blob_name: str, filename: str) -> Dict:
        """画像をCloud Storageにアップロード（非公開）し、署名付きURLとBase64を返す"""
        try:
            # 画像をバイト形式で保存
            img_byte_arr = io.BytesIO()
            save_format = image.format if image.format else 'PNG'
            image.save(img_byte_arr, format=save_format)
            
            # 完全なblob名を生成
            full_blob_name = f"{Config.PROCESSED_IMAGES_PREFIX}{blob_name}.{save_format.lower()}"
            blob = self.bucket.blob(full_blob_name)
            
            # アップロード（公開しない）
            blob.upload_from_string(
                img_byte_arr.getvalue(), 
                content_type=f"image/{save_format.lower()}"
            )
            # 署名付きURLは使わない（権限不要な方式）。代わりにダウンロードAPIを利用
            signed_url = None

            # クライアント表示用のData URL（プレビュー用）
            base64_data = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
            data_url = f"data:image/{save_format.lower()};base64,{base64_data}"

            return {
                "blob_name": full_blob_name,
                "signed_url": signed_url,
                "size": len(img_byte_arr.getvalue()),
                "data_url": data_url
            }
            
        except Exception as e:
            raise Exception(f"画像のアップロードに失敗しました: {str(e)}")
    
    def download_image(self, blob_name: str) -> Image.Image:
        """Cloud Storageから画像をダウンロード"""
        try:
            blob = self.bucket.blob(blob_name)
            image_data = blob.download_as_bytes()
            return Image.open(io.BytesIO(image_data))
            
        except Exception as e:
            raise Exception(f"画像のダウンロードに失敗しました: {str(e)}")

    def delete_blob(self, blob_name: str) -> None:
        """指定したBlobを削除"""
        try:
            blob = self.bucket.blob(blob_name)
            blob.delete()
        except Exception:
            pass
    
    def list_images(self) -> List[Dict]:
        """保存された画像の一覧を取得"""
        try:
            blobs = self.bucket.list_blobs(prefix=Config.PROCESSED_IMAGES_PREFIX)
            
            images = []
            for blob in blobs:
                if any(blob.name.endswith(ext) for ext in Config.ALLOWED_IMAGE_FORMATS):
                    images.append({
                        "name": blob.name,
                        "url": blob.public_url,
                        "size": blob.size,
                        "created": blob.time_created.isoformat() if blob.time_created else None
                    })
            
            return images
            
        except Exception as e:
            raise Exception(f"画像一覧の取得に失敗しました: {str(e)}")
    