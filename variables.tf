variable "aws_region" {
  description = "AWS region to deploy infrastructure"
  type        = string
  default     = "us-east-1"
}

variable "bucket_prefix" {
  default = "secure-bucket"
}

locals {
  bucket_name = "${var.bucket_prefix}-${random_id.suffix.hex}"
}