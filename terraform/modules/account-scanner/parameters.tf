# Parameter Store resources for account configuration
# These parameters are read by the Lambda function at runtime

resource "aws_ssm_parameter" "slack_token" {
  name        = "/org-scanner/${var.account_name}/slack-token"
  description = "Slack bot token for ${var.account_name} scanner"
  type        = "SecureString"
  value       = var.slack_token

  tags = {
    Account = var.account_name
  }
}

resource "aws_ssm_parameter" "slack_signing_secret" {
  name        = "/org-scanner/${var.account_name}/slack-signing-secret"
  description = "Slack app signing secret for ${var.account_name} manual scan button"
  type        = "SecureString"
  value       = var.slack_signing_secret

  tags = {
    Account = var.account_name
  }
}

resource "aws_ssm_parameter" "users_mapping" {
  name        = "/org-scanner/${var.account_name}/users-mapping"
  description = "Account name to email mapping for ${var.account_name}"
  type        = "SecureString"
  value       = jsonencode(var.users_mapping)

  tags = {
    Account = var.account_name
  }
}

resource "aws_ssm_parameter" "ou_id" {
  name        = "/org-scanner/${var.account_name}/ou-id"
  description = "${var.account_name} Organizational Unit ID"
  type        = "String"
  value       = var.ou_id

  tags = {
    Account = var.account_name
  }
}

resource "aws_ssm_parameter" "regions" {
  name        = "/org-scanner/${var.account_name}/regions"
  description = "AWS regions to scan for ${var.account_name}"
  type        = "String"
  value       = join(",", var.scan_regions)

  tags = {
    Account = var.account_name
  }
}

resource "aws_ssm_parameter" "scan_toggles" {
  name        = "/org-scanner/${var.account_name}/scan-toggles"
  description = "Resource types to scan for ${var.account_name}"
  type        = "String"
  value       = jsonencode(var.scan_toggles)

  tags = {
    Account = var.account_name
  }
}

resource "aws_ssm_parameter" "monitoring_channel" {
  name        = "/org-scanner/${var.account_name}/monitoring-channel"
  description = "Slack channel for monitoring alerts"
  type        = "String"
  value       = var.monitoring_channel

  tags = {
    Account = var.account_name
  }
}
