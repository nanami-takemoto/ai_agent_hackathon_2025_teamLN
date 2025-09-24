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

export REGION="asia-northeast1"
export REPO="<your-repo>"         # 例: image-processor-repo
export IMAGE="<your-image>"       # 例: image-processor
export PROJECT_ID="<your-project>"

docker build --platform linux/amd64 -f docker/Dockerfile \
  -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE}:latest .

docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE}:latest
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
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE}:latest \
  --region=${REGION} --platform=managed --allow-unauthenticated \
  --memory=1Gi --cpu=1 --max-instances=5
```

