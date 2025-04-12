#!/bin/bash
set -e

# Load non-sensitive values directly
export S3_BUCKET_NAME=$(terraform output -raw bucket_name)
export AWS_KMS_KEY_ARN=$(terraform output -raw kms_key_arn)
export ADMIN_USER_ARN=$(terraform output -raw admin_user_arn)

# For sensitive credentials, use JSON output
TF_CREDS=$(terraform output -json admin_credentials)
export ADMIN_ACCESS_KEY=$(echo "$TF_CREDS" | jq -r .access_key)
export ADMIN_SECRET_KEY=$(echo "$TF_CREDS" | jq -r .secret_key)

# Debug print (mask sensitive values)
echo "Using bucket: $S3_BUCKET_NAME"
echo "Uploading with KMS key: $AWS_KMS_KEY_ARN"
echo "ADMIN_USER_ARN: $ADMIN_USER_ARN"
echo "Using access key: ${ADMIN_ACCESS_KEY:0:4}...${ADMIN_ACCESS_KEY: -4}"

# Pass through to Python script
python3 ./script/secure_uploader.py "$@"
#set -e
#
## Load values from Terraform output
#TF_OUTPUTS="credentials.json"
#
#export S3_BUCKET_NAME=$(jq -r '.bucket_name.value' $TF_OUTPUTS)
#export AWS_KMS_KEY_ARN=$(jq -r '.kms_key_arn.value' $TF_OUTPUTS)
#export ADMIN_USER_ARN=$(jq -r '.admin_user_arn.value' $TF_OUTPUTS)
#export EDITOR_USER_ARN=$(jq -r '.editor_user_arn.value' $TF_OUTPUTS)
#
## Try to load direct credentials if available
#if jq -e '.admin_access_key.value' $TF_OUTPUTS >/dev/null 2>&1; then
#  export ADMIN_ACCESS_KEY=$(jq -r '.admin_access_key.value' $TF_OUTPUTS)
#  export ADMIN_SECRET_KEY=$(jq -r '.admin_secret_key.value' $TF_OUTPUTS)
#fi
#
## Debug print
#echo "Using bucket: $S3_BUCKET_NAME"
#echo "Uploading with KMS key: $AWS_KMS_KEY_ARN"
#echo "ADMIN_USER_ARN: $ADMIN_USER_ARN"
#
## Pass through to Python script
#python3 ./script/secure_uploader.py "$@"
