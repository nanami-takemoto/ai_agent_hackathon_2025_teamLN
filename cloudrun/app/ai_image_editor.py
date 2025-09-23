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
        """Vertex AI Imagen APIのinpaintで、人物の手(花束)で顔を隠す編集を全体画像に適用"""
        try:
            # 顔領域から上半身（肩周りまで）をカバーする大きめマスクを生成
            mask_b64 = self._create_upper_body_mask(image.size, face_regions)

            # プロンプト（ユーザー指定: 花束で顔を隠す）
            base_prompt = (
                "The subject should naturally raise both hands to hold a bouquet of baby's breath (Gypsophila), "
                "positioned directly in front of their face. "
                "The bouquet should be slightly larger than the subject's face, partially obscuring it, "
                "and must appear natural, fresh, delicate, and abundant. "
                "Both hands holding the bouquet should look natural with correct perspective, skin tone, and realistic shading. "
                "Maintain the original hair, clothing, background, and lighting from the input image without any changes. "
                "Photorealistic and seamless editing."
            )

            negative_prompt = (
                "mutated hands, fused fingers, broken anatomy, deformed face, distorted arms, "
                "extra limbs, floating hands, blurry, text, watermark, stickers, emojis, drawn graphics"
            )

            prompt = f"{base_prompt} Negative prompt: {negative_prompt}"

            edited = self._inpaint_full_image_with_imagen(image, mask_b64, prompt)
            return edited, None

        except Exception as e:
            error_msg = f"Failed during image generation setup: {e}"
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

    def _create_upper_body_mask(self, image_size: Tuple[int, int], face_regions: List[Tuple[int, int, int, int]]) -> str:
        """上半身（顔〜肩周り）を覆うマスクを生成"""
        from PIL import ImageDraw
        width, height = image_size
        mask = Image.new('L', (width, height), 0)
        draw = ImageDraw.Draw(mask)
        for (x, y, w, h) in face_regions:
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
        self, image: Image.Image, mask_b64: str, prompt: str
    ) -> Optional[Image.Image]:
        try:
            client_options = {"api_endpoint": f"{Config.IMAGEN_REGION}-aiplatform.googleapis.com"}
            client = aiplatform_v1.PredictionServiceClient(client_options=client_options)

            endpoint = f"projects/{Config.PROJECT_ID}/locations/{Config.IMAGEN_REGION}/publishers/google/models/imagegeneration@006"

            # Base64エンコード
            buf = io.BytesIO()
            image.convert('RGB').save(buf, format='JPEG', quality=95)
            image_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

            instance_dict = {
                "prompt": prompt,
                "image": {"bytesBase64Encoded": image_b64},
                "mask": {"image": {"bytesBase64Encoded": mask_b64}},
            }
            instance = struct_pb2.Value()
            ParseDict(instance_dict, instance)


            parameters_dict = {
                "sampleCount": 1,
                "action": "inpaint",
                "safetyFilterLevel": "block_some",
                "personGeneration": "allow_adult",
            }
            parameters = struct_pb2.Value()
            ParseDict(parameters_dict, parameters)

            response = client.predict(endpoint=endpoint, instances=[instance], parameters=parameters)

            if response.predictions:
                # Convert first prediction to dict and extract bytes
                pred_dict = MessageToDict(response._pb).get('predictions', [{}])[0]
                b64 = pred_dict.get('bytesBase64Encoded')
                if b64:
                    data = base64.b64decode(b64)
                    return Image.open(io.BytesIO(data))
        
            # 予測が空の場合も失敗と見なす
            raise Exception(f"Prediction result was empty. Full response: {response}")

        except Exception as e:
            # 失敗時は呼び出し元に例外を投げてエラー内容を伝える
            raise Exception(f"Imagen API prediction failed: {e}")
    
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
    
    def edit_image_with_ai(self, image: Image.Image, face_regions: List[Tuple[int, int, int, int]], edit_type: str = "peace_sign") -> Dict:
        """AIを使用して画像を編集"""
        if edit_type == "peace_sign":
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
        else:
            raise Exception(f"サポートされていない編集タイプ: {edit_type}")
