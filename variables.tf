# プロジェクト設定
variable "project_id" {
  description = "Google Cloud プロジェクトID"
  type        = string
  default     = "gcp-zenn-hackathon-2025"
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

# リソース設定
variable "cpu_limit" {
  description = "Cloud RunサービスのCPU制限"
  type        = string
  default     = "1"
}

variable "memory_limit" {
  description = "Cloud Runサービスのメモリ制限"
  type        = string
  default     = "1Gi"
}

variable "max_instances" {
  description = "Cloud Runサービスの最大インスタンス数"
  type        = number
  default     = 5
}

# サービスアカウント設定
variable "service_account_email" {
  description = "Cloud Runサービスで使用するサービスアカウントのメールアドレス"
  type        = string
}
