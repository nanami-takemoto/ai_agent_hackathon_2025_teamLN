# プロジェクト設定
variable "project_id" {
  description = "Google Cloud プロジェクトID"
  type        = string
}

variable "region" {
  description = "Google Cloud リージョン"
  type        = string
  default     = "asia-northeast1"
}

# Cloud Run設定
variable "service_name" {
  description = "Cloud Runサービス名"
  type        = string
  default     = "image-processor"
}

variable "container_image_url" {
  description = "Cloud Runで使用するコンテナイメージのURL"
  type        = string
}

# Cloud Storage設定
variable "bucket_name" {
  description = "Cloud Storageバケット名"
  type        = string
}

# Artifact Registry設定
variable "artifact_registry_repository_id" {
  description = "Artifact RegistryリポジトリID"
  type        = string
}

# リソース設定
variable "cpu_limit" {
  description = "Cloud RunサービスのCPU制限"
  type        = string
  default     = "2"
}

variable "memory_limit" {
  description = "Cloud Runサービスのメモリ制限"
  type        = string
  default     = "2Gi"
}

variable "max_instances" {
  description = "Cloud Runサービスの最大インスタンス数"
  type        = number
  default     = 5
}

variable "max_concurrency" {
  description = "1インスタンスあたりの同時処理数（リクエスト並列数）"
  type        = number
  default     = 1
}

variable "request_timeout" {
  description = "リクエストタイムアウト（例: 120s）"
  type        = string
  default     = "120s"
}

# Vertex AI / Imagen 設定
variable "vision_endpoint_id" {
  description = "Vertex AI Vision推論エンドポイントID（未指定なら検出スキップ）"
  type        = string
  default     = ""
}

variable "vision_region" {
  description = "Vertex AI Visionのリージョン（未指定時はregionを使用）"
  type        = string
  default     = ""
}

variable "imagen_region" {
  description = "Imagen/Generative Images のリージョン"
  type        = string
  default     = "us-central1"
}

variable "imagen_model" {
  description = "使用するImagenモデル名"
  type        = string
  default     = "imagen-3.0-generate-001"
}

variable "sdxl_model" {
  description = "使用するSDXL Inpaintingモデル名"
  type        = string
  default     = "imagegeneration@006"
}

variable "sdxl_region" {
  description = "SDXL Inpaintingのリージョン"
  type        = string
  default     = "us-central1"
}
