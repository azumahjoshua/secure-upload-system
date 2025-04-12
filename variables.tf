variable "aws_region" {
  description = "AWS region to deploy infrastructure"
  type        = string
  default     = "us-east-1"
}

# variable "bucket_prefix" {
#   default = "secure-bucket"
# }

# variable "account_id" {
#   default = ""
# }

locals {
  bucket_name   = "secure-bucket-${random_id.suffix.hex}"
  policy_suffix = random_id.suffix.hex
}