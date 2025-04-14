#!/bin/bash
set -eo pipefail

# Configuration
TF_DIR="./"
LOG_FILE="deploy-$(date +%Y%m%d).log"
#TF_BUCKET="secure-upload-system2024040322"
#REGION="us-east-1"

log() {
    echo -e "\n[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

#init_backend() {
#    log "Configuring S3 backend..."
#
#    if aws s3api head-bucket --bucket "$TF_BUCKET" 2>/dev/null; then
#        log "S3 bucket $TF_BUCKET already exists. Skipping creation."
#    else
#        log "Creating S3 bucket $TF_BUCKET..."
#        aws s3api create-bucket --bucket "$TF_BUCKET" --region $REGION
#    fi
#
#    aws s3api put-public-access-block \
#        --bucket "$TF_BUCKET" \
#        --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
#
#    aws s3api put-bucket-versioning --bucket "$TF_BUCKET" --versioning-configuration Status=Enabled
#}

deploy() {
    cd "$TF_DIR"
    terraform fmt
    terraform init -reconfigure
    terraform validate
    terraform plan -out=tfplan

#    if [[ $confirm == "yes" || "y"  || "YES" ]]; then
    read -p "Apply changes? (yes/no): " confirm
    if [[ "$confirm" =~ ^(yes|y|YES|Y)$ ]]; then
        terraform apply tfplan
        terraform output -json admin_credentials > credentials.json
    fi
}

main() {
#    init_backend
    deploy
    log "Deployment complete. Log: $LOG_FILE"
}

main 2>&1 | tee -a "$LOG_FILE"



#set -eo pipefail
#
## Configuration
#TF_DIR="./"
#LOG_FILE="deploy-$(date +%Y%m%d).log"
#TF_BUCKET="secure-upload-system2024040322"
#
#log() {
#    echo -e "\n[$(date +'%Y-%m-%d %H:%M:%S')] $1"
#}
#
#init_backend() {
#    log "Configuring S3 backend..."
#    aws s3api create-bucket --bucket $TF_BUCKET --region us-east-1
#    aws s3api put-public-access-block \
#        --bucket $TF_BUCKET \
#        --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
#    aws s3api put-bucket-versioning --bucket $TF_BUCKET --versioning-configuration Status=Enabled
#}
#
#deploy() {
#    cd "$TF_DIR"
#    terraform init -reconfigure
#    terraform validate
#    terraform plan -out=tfplan
#    terraform output -json > tf_outputs.json
#
#    read -p "Apply changes? (yes/no): " confirm
#    [[ $confirm == "yes" ]] && terraform apply tfplan
#}
#
#main() {
#    init_backend
#    deploy
#    log "Deployment complete. Log: $LOG_FILE"
#}
#
#main | tee -a "$LOG_FILE"

