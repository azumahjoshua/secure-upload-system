variable "bucket_name" {
  description = "Name of the S3 bucket"
  type        = string
}

variable "policy_name" {
  description = "Policy Name"
  type        = string
}
variable "kms_key_arn" {
  description = "ARN of the KMS key for encryption"
  type        = string
}

variable "permission_level" {
  description = "Permission level (admin, uploader, or viewer)"
  type        = string
  default     = "uploader"
  validation {
    condition     = contains(["admin", "uploader", "viewer"], var.permission_level)
    error_message = "Permission level must be one of: admin, uploader, viewer"
  }
}