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

# プロジェクト情報
output "project_id" {
  description = "Google Cloud プロジェクトID"
  value       = var.project_id
}

output "region" {
  description = "Google Cloud リージョン"
  value       = var.region
}
