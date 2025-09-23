# API 仕様

## ヘルスチェック
GET /

## 画像処理（Base64）
POST /process
- body: { "image": "base64", "filename": "image" }

## 画像処理（Cloud Storage）
POST /process-from-storage
- body: { "blob_name": "path/to/image" }

## 画像一覧
GET /images

## 顔マスキング（Base64）
POST /mask-faces
- body: { "image": "base64", "filename": "masked_image" }

## 顔マスキング（Cloud Storage）
POST /mask-faces-from-storage
- body: { "blob_name": "path/to/image" }

## AI画像編集（Imagen）
POST /ai-edit
- body: { "image": "base64", "filename": "ai_edited_image", "edit_type": "peace_sign" }
