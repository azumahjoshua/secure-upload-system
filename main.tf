provider "random" {}

resource "random_id" "suffix" {
  byte_length = 4
}


# 1. Create KMS module
module "kms" {
  source          = "./modules/kms"
  key_alias       = "secure-uploads-key"
  upload_role_arn = module.iam_role.role_arn
  deletion_window = 30
}

# 2. Create S3 bucket
module "s3" {
  source             = "./modules/s3"
  bucket_name        = local.bucket_name
  kms_key_arn        = module.kms.key_arn
  versioning_enabled = true
  expiration_days    = 2
  allowed_user_agent = "secure_uploader"
}

# 3. Create the base IAM policy
module "iam_policy" {
  source      = "./modules/iam_policy"
  policy_name = "${local.bucket_name}-base-policy"
  bucket_name = module.s3.bucket_name
  kms_key_arn = module.kms.key_arn
}

# 4. Create IAM role
module "iam_role" {
  source           = "./modules/iam_role"
  role_name        = "${local.bucket_name}-upload-role"
  policy_arn       = module.iam_policy.policy_arn
  trusted_services = ["lambda.amazonaws.com"]
  # trusted_principals = ["arn:aws:iam::${var.account_id}:user/joshua"]
  # allowed_ips     = ["192.0.2.0/24"]
}

# 5. Update KMS policy to include the role ARN
resource "aws_kms_key_policy" "update_policy" {
  key_id = module.kms.key_id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EnableRootPermissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "EnableRolePermissions"
        Effect = "Allow"
        Principal = {
          AWS = module.iam_role.role_arn
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })
}

data "aws_caller_identity" "current" {}

# 6. Create role-specific policies
module "admin_policy" {
  source           = "./modules/iam_policy"
  policy_name      = "${local.bucket_name}-admin-policy-${local.policy_suffix}"
  bucket_name      = module.s3.bucket_name
  kms_key_arn      = module.kms.key_arn
  permission_level = "admin"
  # allowed_ips     = ["192.0.2.0/24"]
}

module "editor_policy" {
  source           = "./modules/iam_policy"
  policy_name      = "${local.bucket_name}-editor-policy"
  bucket_name      = module.s3.bucket_name
  kms_key_arn      = module.kms.key_arn
  permission_level = "editor"
  # allowed_ips      = ["192.0.2.0/24"]
}

# module "viewer_policy" {
#   source           = "./modules/iam_policy"
#   policy_name      = "${local.bucket_name}-viewer-policy"
#   bucket_name      = module.s3.bucket_name
#   kms_key_arn      = module.kms.key_arn
#   permission_level = "viewer"
# }

# Create users
resource "aws_iam_user" "admin_user" {
  name = "${local.bucket_name}-admin"
}

resource "aws_iam_user" "editor_user" {
  name = "${local.bucket_name}-editor"
}

# resource "aws_iam_user" "viewer_user" {
#   name = "${local.bucket_name}-viewer"
# }

# Create access keys
resource "aws_iam_access_key" "admin_user" {
  user = aws_iam_user.admin_user.name
}

resource "aws_iam_access_key" "editor_user" {
  user = aws_iam_user.editor_user.name
}

# resource "aws_iam_access_key" "viewer_user" {
#   user = aws_iam_user.viewer_user.name
# }

# Attach policies
resource "aws_iam_user_policy_attachment" "admin_policy" {
  user       = aws_iam_user.admin_user.name
  policy_arn = module.admin_policy.policy_arn
}

resource "aws_iam_user_policy_attachment" "editor_policy" {
  user       = aws_iam_user.editor_user.name
  policy_arn = module.editor_policy.policy_arn
}

# resource "aws_iam_user_policy_attachment" "viewer_policy" {
#   user       = aws_iam_user.viewer_user.name
#   policy_arn = module.viewer_policy.policy_arn
# }
