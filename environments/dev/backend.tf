terraform {
  backend "s3" {
    bucket         = "secure-upload-system2024040322"
    key            = "env:/dev/terraform.tfstate" 
    region         = "us-east-1"
  }
}