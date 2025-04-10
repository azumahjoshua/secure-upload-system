resource "aws_iam_role" "s3_upload_role" {
  name               = var.role_name
  assume_role_policy = data.aws_iam_policy_document.assume_role_policy.json
}

data "aws_iam_policy_document" "assume_role_policy" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = var.trusted_services
    }
  }
}

resource "aws_iam_role_policy_attachment" "s3_upload_policy_attachment" {
  role       = aws_iam_role.s3_upload_role.name
  policy_arn = var.policy_arn
}