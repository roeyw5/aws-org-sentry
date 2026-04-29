# API Gateway HTTP API for Slack button trigger
# Allows operators to trigger manual scans via Slack without waiting for scheduled scans

resource "aws_apigatewayv2_api" "slack_trigger" {
  name          = "slack-trigger-${var.account_name}"
  protocol_type = "HTTP"
  description   = "Slack button trigger for manual ${var.account_name} scans"

  tags = {
    Account = var.account_name
  }
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.slack_trigger.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.scanner.arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "scan" {
  api_id    = aws_apigatewayv2_api.slack_trigger.id
  route_key = "POST /scan"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.slack_trigger.id
  name        = "$default"
  auto_deploy = true

  tags = {
    Account = var.account_name
  }
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scanner.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.slack_trigger.execution_arn}/*/*"
}
