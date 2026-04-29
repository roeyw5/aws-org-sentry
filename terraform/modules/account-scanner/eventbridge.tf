resource "aws_scheduler_schedule" "morning_scan" {
  count = var.enable_schedules ? 1 : 0

  name       = "aws-scanner-${var.account_name}-morning"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = "cron(${var.morning_scan_cron})"
  schedule_expression_timezone = var.schedule_timezone

  target {
    arn      = aws_lambda_function.scanner.arn
    role_arn = aws_iam_role.eventbridge.arn
  }
}

resource "aws_scheduler_schedule" "evening_scan" {
  count = var.enable_schedules ? 1 : 0

  name       = "aws-scanner-${var.account_name}-evening"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = "cron(${var.evening_scan_cron})"
  schedule_expression_timezone = var.schedule_timezone

  target {
    arn      = aws_lambda_function.scanner.arn
    role_arn = aws_iam_role.eventbridge.arn
  }
}

# IAM role for EventBridge Scheduler to invoke Lambda
resource "aws_iam_role" "eventbridge" {
  name = "aws-scanner-${var.account_name}-eventbridge-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "scheduler.amazonaws.com"
      }
    }]
  })

  tags = {
    Account = var.account_name
  }
}

resource "aws_iam_role_policy" "eventbridge_invoke_lambda" {
  name = "invoke-lambda"
  role = aws_iam_role.eventbridge.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = aws_lambda_function.scanner.arn
    }]
  })
}
