# Lambda execution role
resource "aws_iam_role" "lambda" {
  name = "aws-scanner-${var.account_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = {
    Account = var.account_name
  }
}

moved {
  from = aws_iam_role_policy.lambda_assume_student_roles
  to   = aws_iam_role_policy.lambda_assume_target_account_roles
}

# Cross-account permissions policy
resource "aws_iam_role_policy" "lambda_assume_target_account_roles" {
  name = "assume-target-account-roles"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["sts:AssumeRole"]
        Resource = "arn:aws:iam::*:role/${var.assume_role_name}"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = "arn:aws:ssm:${var.region}:${var.tooling_account_id}:parameter/org-scanner/${var.account_name}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.region}:${var.tooling_account_id}:log-group:/aws/lambda/aws-scanner-${var.account_name}:*"
      }
    ]
  })
}
