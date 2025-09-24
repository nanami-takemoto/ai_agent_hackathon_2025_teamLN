"""APIエンドポイント定義"""
import io
from flask import Blueprint, request, jsonify
from flask import send_file
from image_processor import ImageProcessor
from storage_service import StorageService
from face_detector import FaceDetector
from ai_image_editor import AIImageEditor
from config import Config

# ブループリントを作成
api = Blueprint('api', __name__)

# すべての未捕捉例外をJSONで返す（HTTP 200）
@api.errorhandler(Exception)
def handle_api_error(e):
    return jsonify({
        "status": "error",
        "message": "unhandled_exception",
        "fallback_used": True,
        "debug_error": str(e)
    })

# サービスインスタンス
image_processor = ImageProcessor()
storage_service = StorageService()
face_detector = FaceDetector()
ai_image_editor = AIImageEditor()

@api.route('/', methods=['GET'])
def health_check():
    """ヘルスチェックエンドポイント"""
    return jsonify({
        "status": "healthy",
        "service": "image-processor",
        "bucket": Config.BUCKET_NAME,
        "project": Config.PROJECT_ID,
        "region": Config.REGION
    })

@api.route('/process', methods=['POST'])
def process_image():
    """Base64画像の処理エンドポイント"""
    try:
        # リクエストデータを取得
        data = request.get_json()
        
        if not data or 'image' not in data:
            return jsonify({"error": "画像データが必要です"}), 400
        
        # Base64画像をデコード
        image = image_processor.decode_base64_image(data['image'])
        
        # 画像を検証
        image_processor.validate_image(image)
        
        # 画像を処理
        processed_image = image_processor.process_image(image)
        
        # 画像情報を取得
        image_info = image_processor.get_image_info(processed_image)
        
        # Cloud Storageにアップロード
        filename = data.get('filename', 'image')
        upload_result = storage_service.upload_image(processed_image, filename, filename)
        response_json = {
            "status": "success",
            "image_info": image_info,
            "signed_url": upload_result.get("signed_url"),
            "blob_name": upload_result["blob_name"],
            "data_url": upload_result.get("data_url"),
            "message": "画像が正常に処理され、Cloud Storageに保存されました"
        }
        # 即時削除（プレビューはdata_urlで保持）
        print("mask-faces result", {"faces": len(face_regions), "fallback_used": False})
        storage_service.delete_blob(upload_result["blob_name"])
        return jsonify(response_json)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@api.route('/download', methods=['GET'])
def download_blob():
    """非公開バケットから画像を安全にダウンロードするためのプロキシ"""
    try:
        blob_name = request.args.get('blob_name')
        if not blob_name:
            return jsonify({"error": "blob_nameが必要です"}), 400

        image = storage_service.download_image(blob_name)
        img_byte = io.BytesIO()
        fmt = image.format if image.format else 'PNG'
        image.save(img_byte, format=fmt)
        img_byte.seek(0)
        return send_file(img_byte, mimetype=f'image/{fmt.lower()}')
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@api.route('/process-from-storage', methods=['POST'])
def process_image_from_storage():
    """Cloud Storageから画像を読み込んで処理するエンドポイント"""
    try:
        # リクエストデータを取得
        data = request.get_json()
        
        if not data or 'blob_name' not in data:
            return jsonify({"error": "blob_nameが必要です"}), 400
        
        # Cloud Storageから画像を読み込み
        image = storage_service.download_image(data['blob_name'])
        
        # 画像を検証
        image_processor.validate_image(image)
        
        # 画像を処理
        processed_image = image_processor.process_image(image)
        
        # 画像情報を取得
        image_info = image_processor.get_image_info(processed_image, data['blob_name'])
        
        # 処理済み画像を新しい名前で保存
        original_filename = data['blob_name'].split('/')[-1]
        processed_filename = f"processed_{original_filename}"
        upload_result = storage_service.upload_image(processed_image, processed_filename, processed_filename)
        response_json = {
            "status": "success",
            "image_info": image_info,
            "signed_url": upload_result.get("signed_url"),
            "blob_name": upload_result["blob_name"],
            "data_url": upload_result.get("data_url"),
            "message": "Cloud Storageから画像を読み込み、処理して保存しました"
        }
        print("ai-edit result", {"faces": len(face_regions), "fallback_used": not bool(face_regions)})
        storage_service.delete_blob(upload_result["blob_name"])
        return jsonify(response_json)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@api.route('/images', methods=['GET'])
def list_images():
    """保存された画像の一覧を取得"""
    try:
        images = storage_service.list_images()
        
        return jsonify({
            "status": "success",
            "images": images,
            "count": len(images)
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@api.route('/mask-faces', methods=['POST'])
def mask_faces():
    """人物写真の顔を花束で隠すエンドポイント"""
    try:
        # リクエストデータを取得
        data = request.get_json()
        
        if not data or 'image' not in data:
            return jsonify({"error": "画像データが必要です"}), 400
        
        # Base64画像をデコード
        image = image_processor.decode_base64_image(data['image'])
        
        # 画像を検証
        image_processor.validate_image(image)
        
        # 画像をバイト形式に変換（顔検出用）
        img_byte_arr = io.BytesIO()
        fmt = image.format if image.format else 'PNG'
        image.convert('RGB').save(img_byte_arr, format=fmt)
        image_bytes = img_byte_arr.getvalue()
        
        # 顔を検出
        face_regions = face_detector.get_face_regions(image_bytes)
        
        # 顔が検出されない場合は200で情報返却（UI側のUXを優先）
        if not face_regions:
            return jsonify({
                "status": "error",
                "message": "顔が検出されませんでした",
                "faces_detected": 0,
                "image_info": image_processor.get_image_info(image),
                "fallback_used": True,
                "debug_error": "NO_FACES"
            })
        
        # edit_typeパラメータを取得（1=花束、2=ポストカード）
        edit_type_code = data.get('edit_type', 1)  # デフォルトは花束
        
        # edit_typeに応じて編集タイプを決定
        if edit_type_code == 1:
            edit_type = "bouquet"  # 花束
        elif edit_type_code == 2:
            edit_type = "postcard"  # ポストカード
        else:
            edit_type = "bouquet"  # デフォルトは花束
        
        # Vertex AI Imagen APIを使用して画像を編集
        edit_result = ai_image_editor.edit_image_with_ai(image, face_regions, edit_type)
        masked_image = edit_result["image"]
        
        # 画像情報を取得
        image_info = image_processor.get_image_info(masked_image)
        image_info["faces_detected"] = len(face_regions)
        image_info["face_regions"] = face_regions
        
        # Cloud Storageにアップロード
        filename = data.get('filename', 'masked_image')
        upload_result = storage_service.upload_image(masked_image, filename, filename)
        response_json = {
            "status": "success",
            "image_info": image_info,
            "signed_url": upload_result.get("signed_url"),
            "blob_name": upload_result["blob_name"],
            "data_url": upload_result.get("data_url"),
            "message": f"{len(face_regions)}個の顔を花束で隠しました",
            "faces_detected": len(face_regions),
            "fallback_used": edit_result["fallback_used"],
            "debug_error": edit_result["error_message"]
        }
        storage_service.delete_blob(upload_result["blob_name"])
        return jsonify(response_json)
        
    except Exception as e:
        # 500を返さず、UIが扱えるJSONで返す
        return jsonify({
            "status": "error",
            "message": "processing_failed",
            "fallback_used": True,
            "debug_error": str(e)
        })

@api.route('/mask-faces-from-storage', methods=['POST'])
def mask_faces_from_storage():
    """Cloud Storageから画像を読み込んで顔を花束で隠すエンドポイント"""
    try:
        # リクエストデータを取得
        data = request.get_json()
        
        if not data or 'blob_name' not in data:
            return jsonify({"error": "blob_nameが必要です"}), 400
        
        # Cloud Storageから画像を読み込み
        image = storage_service.download_image(data['blob_name'])
        
        # 画像を検証
        image_processor.validate_image(image)
        
        # 画像をバイト形式に変換（顔検出用）
        img_byte_arr = io.BytesIO()
        fmt = image.format if image.format else 'PNG'
        image.convert('RGB').save(img_byte_arr, format=fmt)
        image_bytes = img_byte_arr.getvalue()
        
        # 顔を検出
        face_regions = face_detector.get_face_regions(image_bytes)
        
        if not face_regions:
            return jsonify({
                "status": "error",
                "message": "顔が検出されませんでした",
                "faces_detected": 0,
                "image_info": image_processor.get_image_info(image, data['blob_name'])
            }), 400
        
        # Vertex AI Imagen APIを使用して花束を描画
        edit_result = ai_image_editor.edit_image_with_ai(image, face_regions, "peace_sign")
        masked_image = edit_result["image"]

        # 画像情報を取得
        image_info = image_processor.get_image_info(masked_image, data['blob_name'])
        image_info["faces_detected"] = len(face_regions)
        image_info["face_regions"] = face_regions
        
        # 処理済み画像を新しい名前で保存
        original_filename = data['blob_name'].split('/')[-1]
        masked_filename = f"masked_{original_filename}"
        upload_result = storage_service.upload_image(masked_image, masked_filename, masked_filename)
        response_json = {
            "status": "success",
            "image_info": image_info,
            "signed_url": upload_result.get("signed_url"),
            "blob_name": upload_result["blob_name"],
            "data_url": upload_result.get("data_url"),
            "message": f"Cloud Storageから画像を読み込み、{len(face_regions)}個の顔を花束で隠しました",
            "fallback_used": edit_result["fallback_used"],
            "debug_error": edit_result["error_message"]
        }
        storage_service.delete_blob(upload_result["blob_name"])
        return jsonify(response_json)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@api.route('/ai-edit', methods=['POST'])
def ai_edit_image():
    """Vertex AI Imagen APIを使用した画像編集エンドポイント"""
    try:
        # リクエストデータを取得
        data = request.get_json()
        
        if not data or 'image' not in data:
            return jsonify({"error": "画像データが必要です"}), 400
        
        # Base64画像をデコード
        image = image_processor.decode_base64_image(data['image'])
        
        # 画像を検証
        image_processor.validate_image(image)
        
        # 画像をバイト形式に変換（顔検出用）
        img_byte_arr = io.BytesIO()
        fmt = image.format if image.format else 'PNG'
        image.convert('RGB').save(img_byte_arr, format=fmt)
        image_bytes = img_byte_arr.getvalue()
        
        # 顔を検出
        face_regions = face_detector.get_face_regions(image_bytes)
        
        # 顔が検出されない場合はエラー
        if not face_regions:
            return jsonify({
                "status": "error",
                "message": "顔が検出されませんでした",
                "faces_detected": 0,
                "image_info": image_processor.get_image_info(image)
            }), 400
        
        # 編集タイプを取得（デフォルトはpeace_sign）
        edit_type = data.get('edit_type', 'peace_sign')
        
        # Vertex AI Imagen APIを使用して画像を編集
        edit_result = ai_image_editor.edit_image_with_ai(image, face_regions, edit_type)
        edited_image = edit_result["image"]

        # 画像情報を取得
        image_info = image_processor.get_image_info(edited_image)
        image_info["faces_detected"] = len(face_regions)
        image_info["face_regions"] = face_regions
        image_info["edit_type"] = edit_type
        
        # Cloud Storageにアップロード
        filename = data.get('filename', 'ai_edited_image')
        upload_result = storage_service.upload_image(edited_image, filename, filename)
        response_json = {
            "status": "success",
            "image_info": image_info,
            "signed_url": upload_result.get("signed_url"),
            "blob_name": upload_result["blob_name"],
            "data_url": upload_result.get("data_url"),
            "message": f"{len(face_regions)}個の顔を{edit_type}で編集しました" if face_regions else f"顔未検出のためフォールバックで中央に{edit_type}を描画しました",
            "faces_detected": len(face_regions),
            "fallback_used": edit_result["fallback_used"],
            "debug_error": edit_result["error_message"]
        }
        print("ai-edit result", {"faces": len(face_regions), "fallback_used": not bool(face_regions)})
        storage_service.delete_blob(upload_result["blob_name"])
        return jsonify(response_json)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
