"""Vertex AI Imagen APIを使用した画像編集サービス"""
import io
import base64
from typing import List, Tuple, Optional, Dict
from google.cloud import aiplatform
from google.cloud import aiplatform_v1
from google.protobuf.json_format import MessageToDict, ParseDict
from PIL import Image
import json
from config import Config
from google.protobuf import struct_pb2
import time
import traceback
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from PIL import ImageOps
from google.cloud import aiplatform_v1beta1

class AIImageEditor:
    """Vertex AI Imagen APIを使用した画像編集クラス"""
    
    def __init__(self):
        """AI画像編集サービスの初期化"""
        self.project_id = Config.PROJECT_ID
        # Imagenはus-central1推奨
        self.location = Config.IMAGEN_REGION or Config.REGION
        
        # Vertex AIを初期化
        aiplatform.init(project=self.project_id, location=self.location)
    
    def generate_piece_overlay(self, image: Image.Image, face_regions: List[Tuple[int, int, int, int]]) -> Tuple[Optional[Image.Image], Optional[str]]:
        """Vertex AI Imagen APIのinpaintで、人物の手(ピース/花束)で顔を隠す編集を全体画像に適用"""
        try:
            # 入力画像を長辺<=1536に縮小（capability安定化）
            resize_ratio = 1.0
            try:
                max_side = 1536
                if max(image.width, image.height) > max_side:
                    resize_ratio = max_side / float(max(image.width, image.height))
                    new_size = (int(image.width * resize_ratio), int(image.height * resize_ratio))
                    image = image.resize(new_size, Image.Resampling.LANCZOS)
            except Exception:
                resize_ratio = 1.0

            # モデルに応じてマスク生成をスキップ（capability系はマスク非対応）
            model_name = getattr(Config, 'IMAGEN_MODEL', 'imagen-3.0-generate-002')
            if 'capability' in model_name:
                mask_b64 = None
            else:
                # リサイズ後の画像サイズでマスクを生成（リサイズ比率を渡す）
                mask_b64 = self._create_upper_body_mask(image.size, face_regions, resize_ratio)

            # 顔寄りの追加context画像を準備（顔があればその周辺、無ければ中央トリミング）
            face_context_b64 = None
            try:
                if face_regions:
                    x, y, w, h = face_regions[0]
                    pad = int(min(w, h) * 0.6)
                    x0 = max(0, x - pad)
                    y0 = max(0, y - pad)
                    x1 = min(image.width, x + w + pad)
                    y1 = min(image.height, y + h + pad * 2)
                    face_crop = image.crop((x0, y0, x1, y1))
                else:
                    # 顔検出が無い場合は画像中央を正方形で切り出し
                    side = min(image.width, image.height)
                    face_crop = ImageOps.fit(image, (side, side), centering=(0.5, 0.45))
                buf_fc = io.BytesIO()
                face_crop.convert('RGB').save(buf_fc, format='JPEG', quality=95)
                face_context_b64 = base64.b64encode(buf_fc.getvalue()).decode('utf-8')
            except Exception:
                face_context_b64 = None

            # プロンプト（Imagen 3用に最適化: 花束で顔を隠す、約6割被覆・背景/服は維持）
            base_prompt = (
                "A person holding a beautiful bouquet of white baby's breath flowers (Gypsophila) in front of their face, "
                "covering approximately 60% of their facial features including eyes and nose. "
                "The person is wearing the same clothing and standing in the same background as the original image. "
                "The bouquet is held naturally with both hands, fresh and delicate, abundant white flowers. "
                "Maintain the exact same hair color, clothing style, background setting, lighting conditions, and color palette. "
                "Photorealistic image with natural hand positioning and correct anatomy. "
                "The scene should look exactly like the original photo but with the bouquet addition."
            )

            negative_prompt = (
                "mutated hands, fused fingers, broken anatomy, deformed face, distorted arms, "
                "extra limbs, floating hands, blurry, text, watermark, stickers, emojis, drawn graphics"
            )

            prompt_A = f"{base_prompt} Negative prompt: {negative_prompt}"
            prompt_B = (
                f"{base_prompt} Ensure the bouquet hides roughly sixty percent of the face, covering the eyes and nose while keeping hair, clothing and background unchanged. "
                f"Negative prompt: {negative_prompt}"
            )
            prompt_C = (
                f"{base_prompt} Center the bouquet over the facial area so about 60% of the face is obscured; do not alter hair, clothing or background. "
                f"Negative prompt: {negative_prompt}"
            )

            # 入力画像を長辺<=1536に縮小（capability安定化）
            try:
                max_side = 1536
                if max(image.width, image.height) > max_side:
                    ratio = max_side / float(max(image.width, image.height))
                    new_size = (int(image.width * ratio), int(image.height * ratio))
                    image = image.resize(new_size, Image.Resampling.LANCZOS)
            except Exception:
                pass

            # 2段→3段トライ: A → B → C。各プロンプトで最大2回リトライ
            last_error_detail = None
            for variant, pr in [("A", prompt_A), ("B", prompt_B), ("C", prompt_C)]:
                try:
                    attempts = 0
                    while attempts < 2:
                        edited = self._inpaint_full_image_with_imagen(
                            image, mask_b64, pr if pr else prompt_A
                        )
                        if edited is not None:
                            print(f"Imagen edit succeeded with variant={variant}, attempt={attempts+1}")
                            return edited, None
                        attempts += 1
                        time.sleep(0.8)
                except Exception as inner:
                    print(f"Imagen edit failed on variant={variant}: {inner}")
                    last_error_detail = str(inner)
                    continue

            # Imagen失敗時はSDXL Inpaintingを試行
            print("Imagen failed, trying SDXL Inpainting...")
            if mask_b64 is not None:
                try:
                    edited = self._inpaint_with_sdxl(image, mask_b64, prompt_A)
                    if edited is not None:
                        print("SDXL Inpainting succeeded")
                        return edited, None
                except Exception as sdxl_error:
                    print(f"SDXL Inpainting failed: {sdxl_error}")
                    last_error_detail = f"Imagen: {last_error_detail} | SDXL: {str(sdxl_error)}"

            raise Exception(f"All models failed | last_error={last_error_detail}")

        except Exception as e:
            error_msg = f"Failed during image generation setup: {e}"
            print(f"ERROR: {error_msg}")
            return None, error_msg
    
    def generate_postcard_overlay(self, image: Image.Image, face_regions: List[Tuple[int, int, int, int]]) -> Tuple[Optional[Image.Image], Optional[str]]:
        """Vertex AI Imagen APIのinpaintで、人物のポストカードで顔を隠す編集を全体画像に適用"""
        try:
            from datetime import datetime
            
            # 入力画像を長辺<=1536に縮小（capability安定化）
            resize_ratio = 1.0
            try:
                max_side = 1536
                if max(image.width, image.height) > max_side:
                    resize_ratio = max_side / float(max(image.width, image.height))
                    new_size = (int(image.width * resize_ratio), int(image.height * resize_ratio))
                    image = image.resize(new_size, Image.Resampling.LANCZOS)
            except Exception:
                resize_ratio = 1.0

            # モデルに応じてマスク生成をスキップ（capability系はマスク非対応）
            model_name = getattr(Config, 'IMAGEN_MODEL', 'imagen-3.0-generate-002')
            if 'capability' in model_name:
                mask_b64 = None
            else:
                # リサイズ後の画像サイズでマスクを生成（リサイズ比率を渡す）
                mask_b64 = self._create_upper_body_mask(image.size, face_regions, resize_ratio)

            # 現在の日付を取得（日本時間）
            import pytz
            jst = pytz.timezone('Asia/Tokyo')
            now = datetime.now(jst)
            current_date = now.strftime("%Y/%m/%d")
            
            # 季節判定（月に基づく）
            month = now.month
            if month in [12, 1, 2]:
                season = "winter"
                landscape_desc = "snow-covered mountains and clear blue sky"
            elif month in [3, 4, 5]:
                season = "spring"
                landscape_desc = "cherry blossoms and green mountains"
            elif month in [6, 7, 8]:
                season = "summer"
                landscape_desc = "green mountains and bright blue sky"
            else:  # 9, 10, 11
                season = "autumn"
                landscape_desc = "colorful autumn leaves and mountains"
            
            # プロンプト（ポストカード用: 季節の風景画入りポストカードで顔を隠す、約6割被覆・背景/服は維持）
            base_prompt = (
                f"A person holding a cream beige postcard with a beautiful {season} landscape painting. "
                f"The painting shows {landscape_desc} in soft, artistic style. "
                f"The postcard is held naturally in front of their face, covering approximately 60% of their facial features including eyes and nose. "
                f"The landscape artwork is centered on the postcard with elegant composition. "
                f"The person is wearing the same clothing and standing in the same background as the original image. "
                f"Maintain the exact same hair color, clothing style, background setting, lighting conditions, and color palette. "
                f"Photorealistic image with natural hand positioning and correct anatomy. "
                f"The scene should look exactly like the original photo but with the postcard addition."
            )

            negative_prompt = (
                "mutated hands, fused fingers, broken anatomy, deformed face, distorted arms, "
                "extra limbs, floating hands, blurry, text, watermark, stickers, emojis, drawn graphics, "
                "abstract art, modern art, cartoon style, anime style"
            )

            prompt_A = f"{base_prompt} Negative prompt: {negative_prompt}"
            prompt_B = (
                f"{base_prompt} Ensure the postcard hides roughly sixty percent of the face, covering the eyes and nose while keeping hair, clothing and background unchanged. "
                f"The {season} landscape painting should be clearly visible and beautifully rendered. "
                f"Negative prompt: {negative_prompt}"
            )
            prompt_C = (
                f"{base_prompt} Center the postcard over the facial area so about 60% of the face is obscured; do not alter hair, clothing or background. "
                f"The landscape artwork should show {landscape_desc} in artistic style. "
                f"Negative prompt: {negative_prompt}"
            )

            # 2段→3段トライ: A → B → C。各プロンプトで最大2回リトライ
            last_error_detail = None
            for variant, pr in [("A", prompt_A), ("B", prompt_B), ("C", prompt_C)]:
                try:
                    attempts = 0
                    while attempts < 2:
                        edited = self._inpaint_full_image_with_imagen(
                            image, mask_b64, pr if pr else prompt_A
                        )
                        if edited is not None:
                            print(f"Imagen edit succeeded with variant={variant}, attempt={attempts+1}")
                            return edited, None
                        attempts += 1
                        time.sleep(0.8)
                except Exception as inner:
                    print(f"Imagen edit failed on variant={variant}: {inner}")
                    last_error_detail = str(inner)
                    continue

            # Imagen失敗時はSDXL Inpaintingを試行
            print("Imagen failed, trying SDXL Inpainting...")
            if mask_b64 is not None:
                try:
                    edited = self._inpaint_with_sdxl(image, mask_b64, prompt_A)
                    if edited is not None:
                        print("SDXL Inpainting succeeded")
                        return edited, None
                except Exception as sdxl_error:
                    print(f"SDXL Inpainting failed: {sdxl_error}")
                    last_error_detail = f"Imagen: {last_error_detail} | SDXL: {str(sdxl_error)}"

            raise Exception(f"All models failed | last_error={last_error_detail}")

        except Exception as e:
            error_msg = f"Failed during postcard image generation setup: {e}"
            print(f"ERROR: {error_msg}")
            return None, error_msg
    
    def _generate_piece_prompt(self, face_crop: Image.Image, face_index: int) -> str:
        """花束を描画するためのプロンプトを生成"""
        # 顔の特徴に基づいてプロンプトを生成
        width, height = face_crop.size
        
        prompts = [
            f"Make this person pose with a peace sign gesture using their own hand to cover their face, natural hand position, realistic pose, size {width}x{height}",
            f"Edit this person to make a peace sign with their hand and use it to cover their face, natural gesture, realistic pose, {width}x{height} pixels",
            f"Transform this person to pose with a peace sign hand gesture covering their own face, natural and realistic, transparent background",
            f"Make this person use their own hand to make a peace sign and cover their face with it, natural pose, size {width}x{height}, realistic gesture"
        ]
        
        return prompts[face_index % len(prompts)]
    
    def _generate_piece_with_imagen(self, prompt: str, face_crop: Image.Image) -> Image.Image:
        """[Deprecated] 顔切り出しに対するinpaint（互換のため保持）"""
        try:
            # 画像をBase64エンコード
            img_byte_arr = io.BytesIO()
            face_crop.save(img_byte_arr, format='JPEG')
            image_b64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
            
            # リクエスト用のインスタンスを作成（Inpaintアクション用）
            instances = [
                {
                    "prompt": prompt,
                    "image": {
                        "bytesBase64Encoded": image_b64
                    },
                    "mask": {
                        "bytesBase64Encoded": self._create_face_mask(face_crop)
                    }
                }
            ]
            
            # パラメータ設定（Inpaint用）
            parameters = {
                "sampleCount": 1,
                "aspectRatio": "1:1",
                "safetyFilterLevel": "block_some",
                "personGeneration": "allow_adult",
                "action": "inpaint"  # Inpaintアクションを指定
            }
            
            # 予測リクエストを送信
            endpoint = aiplatform.Endpoint(
                endpoint_name=f"projects/{self.project_id}/locations/{self.location}/endpoints/imagen"
            )
            
            response = endpoint.predict(
                instances=instances,
                parameters=parameters
            )
            
            # レスポンスから画像を取得
            if response.predictions:
                prediction = response.predictions[0]
                if 'bytesBase64Encoded' in prediction:
                    image_data = base64.b64decode(prediction['bytesBase64Encoded'])
                    return Image.open(io.BytesIO(image_data))
            
            # エラー時はフォールバック
            return self._create_fallback_piece(face_crop.size)
            
        except Exception as e:
            # エラー時はフォールバック
            return self._create_fallback_piece(face_crop.size)
    
    def _create_face_mask(self, face_crop: Image.Image) -> str:
        """顔領域用のマスクを生成"""
        try:
            # 顔のサイズを取得
            width, height = face_crop.size
            
            # マスク画像を作成（顔の領域を白、背景を黒）
            mask = Image.new('L', (width, height), 0)  # 黒い背景
            
            # 顔の領域を白で塗りつぶし（楕円形）
            from PIL import ImageDraw
            draw = ImageDraw.Draw(mask)
            
            # 顔の領域を楕円形でマスク
            margin = min(width, height) // 10
            draw.ellipse([margin, margin, width - margin, height - margin], fill=255)
            
            # マスクをBase64エンコード
            mask_byte_arr = io.BytesIO()
            mask.save(mask_byte_arr, format='PNG')
            mask_b64 = base64.b64encode(mask_byte_arr.getvalue()).decode('utf-8')
            
            return mask_b64
            
        except Exception as e:
            # エラー時は全体を白いマスクとして返す
            width, height = face_crop.size
            mask = Image.new('L', (width, height), 255)
            mask_byte_arr = io.BytesIO()
            mask.save(mask_byte_arr, format='PNG')
            return base64.b64encode(mask_byte_arr.getvalue()).decode('utf-8')

    def _create_global_face_mask(self, image_size: Tuple[int, int], face_regions: List[Tuple[int, int, int, int]]) -> str:
        """全体画像サイズのマスク（顔+余白）"""
        from PIL import ImageDraw
        width, height = image_size
        mask = Image.new('L', (width, height), 0)
        draw = ImageDraw.Draw(mask)
        for (x, y, w, h) in face_regions:
            pad = int(min(w, h) * 0.40)
            x0 = max(0, x - pad)
            y0 = max(0, y - pad)
            x1 = min(width, x + w + pad)
            y1 = min(height, y + h + pad)
            draw.ellipse([x0, y0, x1, y1], fill=255)
        buf = io.BytesIO()
        mask.save(buf, format='PNG')
        return base64.b64encode(buf.getvalue()).decode('utf-8')

    def _create_upper_body_mask(self, image_size: Tuple[int, int], face_regions: List[Tuple[int, int, int, int]], resize_ratio: float = 1.0) -> str:
        """上半身（顔〜肩周り）を覆うマスクを生成"""
        from PIL import ImageDraw
        width, height = image_size
        mask = Image.new('L', (width, height), 0)
        draw = ImageDraw.Draw(mask)
        for (x, y, w, h) in face_regions:
            # リサイズ比率に応じて座標を調整
            x = int(x * resize_ratio)
            y = int(y * resize_ratio)
            w = int(w * resize_ratio)
            h = int(h * resize_ratio)
            
            pad = int(min(w, h) * 0.60)  # 余白をやや拡大
            x0 = max(0, x - pad)
            y0 = max(0, y - pad)
            x1 = min(width, x + w + pad)
            # 下側は胸〜肩が確実に含まれるように更に拡張
            y1 = min(height, y + int(h * 2.6))
            draw.rectangle([x0, y0, x1, y1], fill=255)
        buf = io.BytesIO()
        mask.save(buf, format='PNG')
        return base64.b64encode(buf.getvalue()).decode('utf-8')

    def _inpaint_full_image_with_imagen(
        self, image: Image.Image, mask_b64: Optional[str], prompt: str
    ) -> Optional[Image.Image]:
        try:
            client_options = {"api_endpoint": f"{Config.IMAGEN_REGION}-aiplatform.googleapis.com"}
            model_name = getattr(Config, 'IMAGEN_MODEL', 'imagen-3.0-generate-001')

            # Generative AI Images API (Imagen 3) 経由で実行
            vertexai.init(project=Config.PROJECT_ID, location=Config.IMAGEN_REGION)
            gen_model = ImageGenerationModel.from_pretrained(model_name)
            # ベース画像（PIL.Imageをそのまま渡す）
            base_pil = image.convert('RGB')

            # Imagen 3でマスク非対応でも画像編集を試行
            # 元画像の特徴を保持しながらプロンプトベースで生成
            
            # 元画像をBase64エンコードしてプロンプトに含める
            img_byte_arr = io.BytesIO()
            base_pil.save(img_byte_arr, format='JPEG', quality=Config.JPEG_QUALITY)
            image_b64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
            
            # プロンプトに元画像の詳細な情報を追加（Imagen 3用）
            enhanced_prompt = f"{prompt} The image should maintain the exact same composition, lighting, and visual style as the original photograph. Keep the same person's appearance, clothing, and background setting unchanged."
            
            try:
                # テキスト生成で画像編集を試行
                images = gen_model.generate_images(
                    prompt=enhanced_prompt,
                    number_of_images=1,
                )
            except Exception as e_generate:
                raise Exception(f"generate_images failed: {e_generate}")

            # 戻りはPIL.Imageの配列相当
            if images and len(images) > 0:
                gen_img = images[0]
                # 一部SDKでは dict 返却のことがあるため両対応
                if isinstance(gen_img, Image.Image):
                    return gen_img
                if hasattr(gen_img, 'image') and isinstance(gen_img.image, Image.Image):
                    return gen_img.image
            raise Exception("Empty predictions from Generative Images API")

        except Exception as e:
            # 失敗時はスタックトレースと可能ならレスポンス/エラー本体を含める
            tb = traceback.format_exc(limit=5)
            detail = getattr(e, 'message', str(e))
            raise Exception(f"Imagen API prediction failed: {detail} | traceback={tb}")
    
    def _inpaint_with_sdxl(
        self, image: Image.Image, mask_b64: str, prompt: str
    ) -> Optional[Image.Image]:
        """Vertex Model Garden SDXL Inpaintingを使用した画像編集"""
        try:
            # SDXL用のクライアント初期化
            client_options = {"api_endpoint": f"{Config.SDXL_REGION}-aiplatform.googleapis.com"}
            client = aiplatform_v1beta1.PredictionServiceClient(client_options=client_options)
            
            # 画像をBase64エンコード
            img_byte_arr = io.BytesIO()
            image.convert('RGB').save(img_byte_arr, format='JPEG', quality=Config.JPEG_QUALITY)
            image_b64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
            
            # リクエスト用のインスタンスを作成
            instances = [
                {
                    "prompt": prompt,
                    "image": {
                        "bytesBase64Encoded": image_b64
                    },
                    "mask": {
                        "image": {
                            "bytesBase64Encoded": mask_b64
                        }
                    }
                }
            ]
            
            # パラメータ設定
            parameters = {
                "sampleCount": 1,
                "aspectRatio": "1:1",
                "safetyFilterLevel": "block_some",
                "personGeneration": "allow_adult",
                "action": "inpaint"
            }
            
            # エンドポイント名
            endpoint_name = f"projects/{Config.PROJECT_ID}/locations/{Config.SDXL_REGION}/publishers/google/models/{Config.SDXL_MODEL}"
            
            # 予測リクエストを送信（タイムアウト設定を延長）
            from google.api_core import timeout
            response = client.predict(
                endpoint=endpoint_name,
                instances=instances,
                parameters=parameters,
                timeout=timeout.ExponentialTimeout(initial=60, maximum=120, multiplier=1.0)
            )
            
            # レスポンスから画像を取得
            if response.predictions:
                prediction = response.predictions[0]
                if 'bytesBase64Encoded' in prediction:
                    image_data = base64.b64decode(prediction['bytesBase64Encoded'])
                    return Image.open(io.BytesIO(image_data))
            
            raise Exception("Empty predictions from SDXL API")
            
        except Exception as e:
            tb = traceback.format_exc(limit=5)
            detail = getattr(e, 'message', str(e))
            raise Exception(f"SDXL API prediction failed: {detail} | traceback={tb}")
    
    def _create_fallback_piece(self, size: Tuple[int, int]) -> Image.Image:
        """フォールバック用の花束画像を生成"""
        width, height = size
        
        # 透明な画像を作成
        piece_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        
        # より目立つ赤い花束を描画
        from PIL import ImageDraw
        draw = ImageDraw.Draw(piece_img)
        
        # 花束の形を描画
        center_x, center_y = width // 2, height // 2
        radius = min(width, height) // 3
        
        # 外側の赤い円
        draw.ellipse([center_x - radius, center_y - radius, center_x + radius, center_y + radius], 
                    fill=(255, 0, 0, 255))
        
        # 内側の白い円
        inner_radius = radius // 2
        draw.ellipse([center_x - inner_radius, center_y - inner_radius, center_x + inner_radius, center_y + inner_radius], 
                    fill=(255, 255, 255, 255))
        
        # 指の部分（V字）
        finger_length = radius // 2
        draw.line([center_x - finger_length, center_y - finger_length, center_x, center_y], 
                 fill=(255, 0, 0, 255), width=5)
        draw.line([center_x, center_y, center_x + finger_length, center_y - finger_length], 
                 fill=(255, 0, 0, 255), width=5)
        
        return piece_img
    
    def _composite_piece(self, base_image: Image.Image, piece_image: Image.Image, x: int, y: int, width: int, height: int) -> Image.Image:
        """花束画像を元の画像に合成"""
        try:
            # 花束画像を顔のサイズに合わせてリサイズ
            resized_piece = piece_image.resize((width, height), Image.Resampling.LANCZOS)
            
            # 透明な画像に合成
            if base_image.mode != 'RGBA':
                base_image = base_image.convert('RGBA')
            
            # 花束画像を重ねる
            base_image.paste(resized_piece, (x, y), resized_piece)
            
            return base_image
            
        except Exception as e:
            raise Exception(f"花束画像の合成に失敗しました: {str(e)}")
    
    def _fallback_piece_generation(self, image: Image.Image, face_regions: List[Tuple[int, int, int, int]]) -> Image.Image:
        """フォールバック用の花束生成"""
        try:
            edited_image = image.copy()
            
            for x, y, width, height in face_regions:
                # フォールバック用の花束画像を生成
                piece_image = self._create_fallback_piece((width, height))
                
                # 元の画像に花束を合成
                edited_image = self._composite_piece(edited_image, piece_image, x, y, width, height)
            
            return edited_image
            
        except Exception as e:
            raise Exception(f"フォールバック用の花束生成に失敗しました: {str(e)}")
    
    def _fallback_postcard_generation(self, image: Image.Image, face_regions: List[Tuple[int, int, int, int]]) -> Image.Image:
        """フォールバック用のポストカード生成"""
        try:
            from datetime import datetime
            edited_image = image.copy()
            
            for x, y, width, height in face_regions:
                # フォールバック用のポストカード画像を生成
                postcard_image = self._create_fallback_postcard((width, height))
                
                # 元の画像にポストカードを合成
                edited_image = self._composite_piece(edited_image, postcard_image, x, y, width, height)
            
            return edited_image
            
        except Exception as e:
            raise Exception(f"フォールバック用のポストカード生成に失敗しました: {str(e)}")
    
    def _create_fallback_postcard(self, size: Tuple[int, int]) -> Image.Image:
        """フォールバック用のポストカード画像を生成（季節の風景画）"""
        from datetime import datetime
        import pytz
        
        width, height = size
        
        # 透明な画像を作成
        postcard_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        
        # ポストカードの背景を描画
        from PIL import ImageDraw
        draw = ImageDraw.Draw(postcard_img)
        
        # ポストカードの形を描画
        center_x, center_y = width // 2, height // 2
        card_width = min(width, height) // 2
        card_height = int(card_width * 1.4)  # ポストカードの縦横比
        
        # ポストカードの背景（クリームベージュ）
        x0 = center_x - card_width // 2
        y0 = center_y - card_height // 2
        x1 = center_x + card_width // 2
        y1 = center_y + card_height // 2
        draw.rectangle([x0, y0, x1, y1], fill=(245, 245, 220, 200))  # クリームベージュ
        
        # 季節判定（月に基づく）
        jst = pytz.timezone('Asia/Tokyo')
        now = datetime.now(jst)
        month = now.month
        
        if month in [12, 1, 2]:
            # 冬：雪景色
            # 山のシルエット
            mountain_y = y0 + card_height // 3
            draw.polygon([x0, mountain_y, x0 + card_width//4, y0 + card_height//6, 
                         x0 + card_width//2, mountain_y, x0 + card_width*3//4, y0 + card_height//8, 
                         x1, mountain_y], fill=(200, 200, 220, 180))
            # 雪
            draw.ellipse([x0 + card_width//6, y0 + card_height//8, x0 + card_width//6 + 8, y0 + card_height//8 + 8], fill=(255, 255, 255, 200))
            draw.ellipse([x0 + card_width//2, y0 + card_height//10, x0 + card_width//2 + 6, y0 + card_height//10 + 6], fill=(255, 255, 255, 200))
            
        elif month in [3, 4, 5]:
            # 春：桜と山
            # 山のシルエット
            mountain_y = y0 + card_height // 3
            draw.polygon([x0, mountain_y, x0 + card_width//4, y0 + card_height//6, 
                         x0 + card_width//2, mountain_y, x0 + card_width*3//4, y0 + card_height//8, 
                         x1, mountain_y], fill=(150, 180, 150, 180))
            # 桜
            draw.ellipse([x0 + card_width//6, y0 + card_height//8, x0 + card_width//6 + 12, y0 + card_height//8 + 12], fill=(255, 200, 220, 200))
            draw.ellipse([x0 + card_width//2, y0 + card_height//10, x0 + card_width//2 + 10, y0 + card_height//10 + 10], fill=(255, 200, 220, 200))
            
        elif month in [6, 7, 8]:
            # 夏：緑の山と空
            # 山のシルエット
            mountain_y = y0 + card_height // 3
            draw.polygon([x0, mountain_y, x0 + card_width//4, y0 + card_height//6, 
                         x0 + card_width//2, mountain_y, x0 + card_width*3//4, y0 + card_height//8, 
                         x1, mountain_y], fill=(100, 150, 100, 180))
            # 太陽
            sun_x = x0 + card_width * 3//4
            sun_y = y0 + card_height//6
            draw.ellipse([sun_x - 8, sun_y - 8, sun_x + 8, sun_y + 8], fill=(255, 220, 100, 200))
            
        else:  # 9, 10, 11
            # 秋：紅葉と山
            # 山のシルエット
            mountain_y = y0 + card_height // 3
            draw.polygon([x0, mountain_y, x0 + card_width//4, y0 + card_height//6, 
                         x0 + card_width//2, mountain_y, x0 + card_width*3//4, y0 + card_height//8, 
                         x1, mountain_y], fill=(180, 120, 80, 180))
            # 紅葉
            draw.ellipse([x0 + card_width//6, y0 + card_height//8, x0 + card_width//6 + 10, y0 + card_height//8 + 10], fill=(255, 150, 50, 200))
            draw.ellipse([x0 + card_width//2, y0 + card_height//10, x0 + card_width//2 + 8, y0 + card_height//10 + 8], fill=(255, 120, 30, 200))
        
        return postcard_img
    
    
    def edit_image_with_ai(self, image: Image.Image, face_regions: List[Tuple[int, int, int, int]], edit_type: str = "bouquet") -> Dict:
        """AIを使用して画像を編集"""
        if edit_type == "bouquet":
            result_image, error_message = self.generate_piece_overlay(image, face_regions)
            fallback_used = error_message is not None
            if fallback_used:
                # フォールバック描画を実行
                result_image = self._fallback_piece_generation(image, face_regions)
            return {
                "image": result_image,
                "fallback_used": fallback_used,
                "error_message": error_message
            }
        elif edit_type == "postcard":
            result_image, error_message = self.generate_postcard_overlay(image, face_regions)
            fallback_used = error_message is not None
            if fallback_used:
                # フォールバック描画を実行
                result_image = self._fallback_postcard_generation(image, face_regions)
            return {
                "image": result_image,
                "fallback_used": fallback_used,
                "error_message": error_message
            }
        elif edit_type == "background_change":
            result_image, error_message = self.change_background(image, face_regions)
            fallback_used = error_message is not None
            if fallback_used:
                # フォールバック描画を実行
                result_image = self._fallback_background_change(image, face_regions)
            return {
                "image": result_image,
                "fallback_used": fallback_used,
                "error_message": error_message
            }
        else:
            raise Exception(f"サポートされていない編集タイプ: {edit_type}")
