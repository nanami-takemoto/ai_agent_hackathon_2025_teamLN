# デプロイ手順

## 環境変数
```
export PROJECT_ID="your-project-id"
export BUCKET_NAME="your-bucket-name"
export REGION="asia-northeast1"
```

## コンテナビルド/プッシュ
```
gcloud auth configure-docker asia-northeast1-docker.pkg.dev
cd cloudrun

docker build --platform linux/amd64 -f docker/Dockerfile \
  -t asia-northeast1-docker.pkg.dev/ai-agent-hackathon-2025-teamln/image-processor-repo/image-processor:latest .

docker push asia-northeast1-docker.pkg.dev/ai-agent-hackathon-2025-teamln/image-processor-repo/image-processor:latest
```

## Terraform（インフラ構築）
- Cloud Runの環境変数はTerraformから注入
- `variables.tf`: project_id, region, など

```
cd terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

## Cloud Run 更新
```
gcloud run deploy image-processor \
  --image=asia-northeast1-docker.pkg.dev/ai-agent-hackathon-2025-teamln/image-processor-repo/image-processor:latest \
  --region=asia-northeast1 --platform=managed --allow-unauthenticated \
  --memory=1Gi --cpu=1 --max-instances=5
```

