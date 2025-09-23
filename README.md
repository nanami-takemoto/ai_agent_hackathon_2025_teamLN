# Image Processor API

Google Cloud Run上で動作する画像処理Webアプリケーションです。Vertex AI Vision APIを使用して人物写真の顔を花束で隠す機能を提供します。

## プロジェクト構成

```
├── cloudrun/             # Cloud Run用アプリケーション
│   ├── app/             # アプリケーションコード
│   │   ├── app.py       # メインアプリケーション
│   │   ├── config.py    # 設定管理
│   │   ├── routes.py    # APIエンドポイント
│   │   ├── image_processor.py # 画像処理ロジック
│   │   ├── storage_service.py # Cloud Storage操作
│   │   ├── face_detector.py # Vertex AI Vision API顔検出
│   │   ├── face_masking.py # 顔マスキング機能
│   │   ├── ai_image_editor.py # Vertex AI Imagen API画像編集
│   │   ├── requirements.txt # Python依存関係
│   │   └── requirements.txt # Python依存関係
│   └── docker/          # Docker設定
│       ├── Dockerfile   # コンテナ設定
│       └── .dockerignore # Docker除外ファイル
└── terraform/           # インフラ設定
    ├── main.tf
    ├── variables.tf
    ├── outputs.tf
    ├── terraform.tfvars
    ├── terraform.tfstate
    ├── terraform.tfstate.backup
    ├── tfplan
    ├── .terraform.lock.hcl
    └── .terraform/      # Terraformキャッシュ
```

## 機能

### 実装済み機能
- ✅ 画像のアップロード・保存
- ✅ 画像の基本情報取得
- ✅ 画像一覧の管理
- ✅ **Vertex AI Vision APIを使用した顔検出**
- ✅ **Vertex AI Imagen APIを使用した画像編集**
- ✅ **人物写真の顔を花束で隠す機能**
- ✅ Cloud Storage連携

## 詳細ドキュメント

- アーキテクチャ: docs/architecture.md
- API仕様: docs/api.md
- デプロイ手順: docs/deployment.md
- セキュリティ: docs/security.md
- 技術スタック: docs/tech_stack.md
- ロードマップ: docs/roadmap.md