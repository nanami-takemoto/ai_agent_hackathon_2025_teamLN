# Cloud RunサービスのURL
output "cloud_run_service_url" {
  description = "Cloud RunサービスのURL"
  value       = google_cloud_run_v2_service.main.uri
}

# Cloud Storageバケット名
output "bucket_name" {
  description = "Cloud Storageバケット名"
  value       = google_storage_bucket.main.name
}

# サービスアカウントのメールアドレス
output "service_account_email" {
  description = "Cloud Runサービスアカウントのメールアドレス"
  value       = google_service_account.cloud_run_sa.email
}

# Artifact Registry情報
output "artifact_registry_repository_name" {
  description = "Artifact Registryリポジトリ名"
  value       = google_artifact_registry_repository.main.name
}

output "artifact_registry_repository_url" {
  description = "Artifact RegistryリポジトリURL"
  value       = google_artifact_registry_repository.main.name
}

output "container_image_url" {
  description = "コンテナイメージの完全なURL"
  value       = var.container_image_url
}

# プロジェクト情報
output "project_id" {
  description = "Google Cloud プロジェクトID"
  value       = var.project_id
}

output "region" {
  description = "Google Cloud リージョン"
  value       = var.region
}
