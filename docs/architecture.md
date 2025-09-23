## ディレクトリ構成（概要）
- cloudrun/
  - app/: Flaskアプリと処理ロジック
  - docker/: Dockerfile 等
- terraform/: GCPインフラ構築一式

# 技術スタック
- Flask: Web API フレームワーク
- Pillow: 画像処理
- Vertex AI Vision API: 顔検出
- Vertex AI Imagen API: 画像編集（Inpaint）
- Google Cloud Storage: 画像保存
- Cloud Run: 実行基盤
- Terraform: インフラ構築

## 論理構成
- API (Flask) → StorageService → Cloud Storage
- API (Flask) → FaceDetector → Vertex AI Vision Endpoint
- API (Flask) → AIImageEditor → Vertex AI Imagen (Inpaint)

# セキュリティ
- 現在は認証なし（本番では認証の導入推奨）
- レート制限の実装を検討
- 依存ライブラリの脆弱性スキャン（pip-audit推奨）
- 環境変数に機密情報を置かない