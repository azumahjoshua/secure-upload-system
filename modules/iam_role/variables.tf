variable "role_name" {
  description = "Name of the IAM role"
  type        = string
}

variable "policy_arn" {
  description = "ARN of the policy to attach to the role"
  type        = string
}

variable "trusted_services" {
  description = "List of AWS services that can assume this role"
  type        = list(string)
  default     = ["ec2.amazonaws.com", "lambda.amazonaws.com"]
}