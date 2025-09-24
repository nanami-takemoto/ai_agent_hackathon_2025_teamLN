# プロバイダ設定
terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# API有効化
resource "google_project_service" "aiplatform_api" {
  project = var.project_id
  service = "aiplatform.googleapis.com"

  disable_dependent_services = false
  disable_on_destroy        = false
}

resource "google_project_service" "run_api" {
  project = var.project_id
  service = "run.googleapis.com"

  disable_dependent_services = false
  disable_on_destroy        = false
}

resource "google_project_service" "storage_api" {
  project = var.project_id
  service = "storage.googleapis.com"

  disable_dependent_services = false
  disable_on_destroy        = false
}

resource "google_project_service" "artifact_registry_api" {
  project = var.project_id
  service = "artifactregistry.googleapis.com"

  disable_dependent_services = false
  disable_on_destroy        = false
}

# Cloud Storageバケット
resource "google_storage_bucket" "main" {
  name          = var.bucket_name
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.storage_api]
}

# Artifact Registryリポジトリ
resource "google_artifact_registry_repository" "main" {
  location      = var.region
  repository_id = var.artifact_registry_repository_id
  description   = "Repository for ${var.service_name} container images"
  format        = "DOCKER"

  depends_on = [google_project_service.artifact_registry_api]
}

# サービスアカウント
resource "google_service_account" "cloud_run_sa" {
  account_id   = "${var.service_name}-sa"
  display_name = "Cloud Run Service Account for ${var.service_name}"
  description  = "Service account for Cloud Run service ${var.service_name}"
}

# IAMロールの付与
resource "google_project_iam_member" "storage_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_project_iam_member" "aiplatform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"

  depends_on = [google_project_service.aiplatform_api]
}

# Artifact Registryへのアクセス権限
resource "google_artifact_registry_repository_iam_member" "artifact_registry_reader" {
  location   = google_artifact_registry_repository.main.location
  repository = google_artifact_registry_repository.main.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Cloud Runサービス
resource "google_cloud_run_v2_service" "main" {
  name     = var.service_name
  location = var.region

  template {
    service_account = google_service_account.cloud_run_sa.email
    
    scaling {
      max_instance_count = var.max_instances
    }

    containers {
      image = var.container_image_url

      resources {
        limits = {
          cpu    = var.cpu_limit
          memory = var.memory_limit
        }
      }

      env {
        name  = "BUCKET_NAME"
        value = google_storage_bucket.main.name
      }

      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "REGION"
        value = var.region
      }

      # 任意: Vertex AI Vision設定（未指定なら空）
      env {
        name  = "VISION_ENDPOINT_ID"
        value = var.vision_endpoint_id
      }

      env {
        name  = "VISION_REGION"
        value = var.vision_region != "" ? var.vision_region : var.region
      }

      # Imagen設定
      env {
        name  = "IMAGEN_REGION"
        value = var.imagen_region
      }

      env {
        name  = "IMAGEN_MODEL"
        value = var.imagen_model
      }

      # SDXL設定
      env {
        name  = "SDXL_MODEL"
        value = var.sdxl_model
      }

      env {
        name  = "SDXL_REGION"
        value = var.sdxl_region
      }
    }

    # 同時実行数 / タイムアウト
    max_instance_request_concurrency = var.max_concurrency
    timeout                          = var.request_timeout
  }

  depends_on = [
    google_project_service.run_api,
    google_project_service.aiplatform_api,
    google_artifact_registry_repository.main
  ]
}

# Cloud Runサービスの公開アクセス許可
resource "google_cloud_run_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.main.location
  service  = google_cloud_run_v2_service.main.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
