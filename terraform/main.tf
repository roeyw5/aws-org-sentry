# Workspace validation - prevents human error
locals {
  workspace_account_match = terraform.workspace == var.account_name || terraform.workspace == "default"
}


# Validation resource - fails fast if workspace/account mismatch
resource "null_resource" "workspace_validation" {
  lifecycle {
    precondition {
      condition     = local.workspace_account_match
      error_message = <<-EOT
        Workspace mismatch detected!
        Current workspace: '${terraform.workspace}'
        Account name in tfvars: '${var.account_name}'

        These must match. Either:
        1. Switch workspace: terraform workspace select ${var.account_name}
        2. Use correct tfvars: terraform apply -var-file=accounts/${terraform.workspace}.tfvars
      EOT
    }
  }
}

# Single module instantiation - workspace determines which account
module "scanner" {
  source = "./modules/account-scanner"

  account_name         = var.account_name
  ou_id                = var.ou_id
  users_mapping        = var.users_mapping
  slack_token          = var.slack_token
  slack_signing_secret = var.slack_signing_secret
  monitoring_channel   = var.monitoring_channel
  morning_scan_cron    = var.morning_scan_cron
  evening_scan_cron    = var.evening_scan_cron
  schedule_timezone    = var.schedule_timezone
  dry_run              = var.dry_run
  test_user_email      = var.test_user_email
  enable_schedules     = var.enable_schedules
  assume_role_name     = var.assume_role_name
  scan_regions         = var.scan_regions
  scan_toggles         = var.scan_toggles

  # Optional threshold overrides — uses module defaults if not specified in tfvars
  threshold_ec2_running_hours  = var.threshold_ec2_running_hours != null ? var.threshold_ec2_running_hours : 12
  threshold_ec2_stopped_hours  = var.threshold_ec2_stopped_hours != null ? var.threshold_ec2_stopped_hours : 672
  threshold_rds_hours          = var.threshold_rds_hours != null ? var.threshold_rds_hours : 5
  threshold_eks_hours          = var.threshold_eks_hours != null ? var.threshold_eks_hours : 12
  threshold_eip_hours          = var.threshold_eip_hours != null ? var.threshold_eip_hours : 2
  threshold_lightsail_hours    = var.threshold_lightsail_hours != null ? var.threshold_lightsail_hours : 168
  threshold_volume_hours       = var.threshold_volume_hours != null ? var.threshold_volume_hours : 672
  threshold_rds_snapshot_hours = var.threshold_rds_snapshot_hours != null ? var.threshold_rds_snapshot_hours : 2160
  threshold_nat_gateway_count  = var.threshold_nat_gateway_count != null ? var.threshold_nat_gateway_count : 0
  threshold_elb_count          = var.threshold_elb_count != null ? var.threshold_elb_count : 0
  threshold_volume_count       = var.threshold_volume_count != null ? var.threshold_volume_count : 5
  threshold_eip_count          = var.threshold_eip_count != null ? var.threshold_eip_count : 2
  threshold_vpc_endpoint_count = var.threshold_vpc_endpoint_count != null ? var.threshold_vpc_endpoint_count : 2
  threshold_lightsail_count    = var.threshold_lightsail_count != null ? var.threshold_lightsail_count : 1
  threshold_ebs_snapshot_count = var.threshold_ebs_snapshot_count != null ? var.threshold_ebs_snapshot_count : 10
  threshold_rds_snapshot_count = var.threshold_rds_snapshot_count != null ? var.threshold_rds_snapshot_count : 5

  depends_on = [null_resource.workspace_validation]
}

output "lambda_arn" {
  description = "Lambda function ARN"
  value       = module.scanner.lambda_arn
}

output "log_group" {
  description = "CloudWatch log group"
  value       = module.scanner.log_group
}

output "parameter_namespace" {
  description = "Parameter Store namespace"
  value       = module.scanner.parameter_namespace
}

output "slack_trigger_url" {
  description = "API Gateway URL for Slack manual scan button"
  value       = module.scanner.slack_trigger_url
}
