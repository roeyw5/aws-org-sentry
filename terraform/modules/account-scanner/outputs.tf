output "lambda_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.scanner.arn
}

output "lambda_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda.arn
}

output "lambda_role_name" {
  description = "Name of the Lambda execution role"
  value       = aws_iam_role.lambda.name
}

output "log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.lambda.name
}

output "parameter_namespace" {
  description = "Parameter Store namespace for this account"
  value       = "/org-scanner/${var.account_name}"
}

output "slack_trigger_url" {
  description = "API Gateway URL for Slack button (use this as Request URL in Slack app Interactivity settings)"
  value       = "${aws_apigatewayv2_api.slack_trigger.api_endpoint}/scan"
}
