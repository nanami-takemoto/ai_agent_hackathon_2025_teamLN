"""MediaPipeを使用した顔検出サービス（Vertex AI Imagenと併用）"""
import io
from typing import List, Dict, Tuple
import mediapipe as mp
from config import Config

class FaceDetector:
    """MediaPipeベースの顔検出クラス"""
    
    def __init__(self):
        """顔検出サービスの初期化"""
        # MediaPipe Face Detection初期化
        # model_selection: 0=近距離, 1=遠距離
        self.mp_face = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
    
    def detect_faces_with_mediapipe(self, image_bytes: bytes) -> List[Dict]:
        """MediaPipeで顔を検出し、画素座標の矩形を返す"""
        try:
            from PIL import Image
            import numpy as np

            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            width, height = image.size
            # MediaPipeの入力はRGB ndarray
            np_img = np.array(image)
            result = self.mp_face.process(np_img)
            faces: List[Dict] = []
            if result.detections:
                for det in result.detections:
                    # MediaPipeは相対座標のbbox
                    bbox = det.location_data.relative_bounding_box
                    x = max(0, int(bbox.xmin * width))
                    y = max(0, int(bbox.ymin * height))
                    w = int(bbox.width * width)
                    h = int(bbox.height * height)
                    # 画像範囲にクリップ
                    w = max(1, min(w, width - x))
                    h = max(1, min(h, height - y))
                    faces.append({
                        'x': x,
                        'y': y,
                        'width': w,
                        'height': h,
                        'confidence': float(det.score[0]) if det.score else 0.0,
                    })
            return faces
        except Exception:
            return []
    
    def get_face_regions(self, image_bytes: bytes) -> List[Tuple[int, int, int, int]]:
        """検出された顔の領域を返す"""
        faces = self.detect_faces_with_mediapipe(image_bytes)
        
        # (x, y, width, height) の形式で返す
        regions = []
        for face in faces:
            regions.append((
                int(face['x']),
                int(face['y']),
                int(face['width']),
                int(face['height'])
            ))
        
        return regions
