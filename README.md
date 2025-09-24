# Peacek - AI画像匿名化ツール
画像をアップロードするだけで簡単匿名化！SNSに公開する前に個人情報を隠そう🚀


## 本リポジトリの趣旨
本リポジトリは、第3回 AI Agent Hackathon with Google Cloud　の応募作品です。

# 基本機能
Peacekは、Google Cloud Run上で動作する画像処理Webアプリケーションで、Vertex AI Imagen APIを使用して人物写真の顔を花束やポストカードで隠す機能を提供します。

## プロジェクト構成

```
├── cloudrun/
│   ├── app/
│   │   ├── app.py                    # Flaskエントリ
│   │   ├── config.py                 # 環境変数ベース設定
│   │   ├── routes.py                 # APIルーティング
│   │   ├── ai_image_editor.py        # 画像編集（Imagen/SDXLフォールバック）
│   │   ├── image_processor.py        # 画像I/O補助
│   │   ├── face_detector.py          # 顔検出
│   │   ├── storage_service.py        # Cloud Storage I/O
│   │   ├── templates/
│   │   │   └── index.html            # WebアプリケーションUI
│   │   ├── static/
│   │   │   └── app.js                # フロントロジック
│   │   └── requirements.txt          # パッケージ依存関係
│   ├── cloudbuild.yaml               # Cloud Build 設定
│   └── docker/
│       └── Dockerfile                # コンテナ定義
├── docs/
│   ├── architecture.md               # アーキテクチャ説明
│   ├── api.md                        # API仕様の解説
│   └── deployment.md                 # デプロイ手順
└── terraform/
    ├── main.tf
    ├── variables.tf                  # 値はtfvarsで管理
    └── outputs.tf
```

## 詳細ドキュメント

- アーキテクチャ: docs/architecture.md
- API仕様: docs/api.md
- デプロイ手順: docs/deployment.md

補足: Terraform の実値は `terraform.tfvars`（非コミット）で管理してください。