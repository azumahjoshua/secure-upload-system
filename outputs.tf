output "bucket_name" {
  value = module.s3.bucket_name
}

output "kms_key_arn" {
  value = module.kms.key_arn
}

output "admin_credentials" {
  value = {
    access_key = aws_iam_access_key.admin_user.id
    secret_key = aws_iam_access_key.admin_user.secret
  }
  sensitive = true
}

output "uploader_credentials" {
  value = {
    access_key = aws_iam_access_key.uploader_user.id
    secret_key = aws_iam_access_key.uploader_user.secret
  }
  sensitive = true
}

output "viewer_credentials" {
  value = {
    access_key = aws_iam_access_key.viewer_user.id
    secret_key = aws_iam_access_key.viewer_user.secret
  }
  sensitive = true
}



