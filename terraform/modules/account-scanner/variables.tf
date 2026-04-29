variable "account_name" {
  description = "Name of the account (e.g., dev, staging, prod)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.account_name))
    error_message = "Account name must contain only lowercase letters, numbers, and hyphens"
  }
}

# Runtime configuration variables removed - now read from Parameter Store by Lambda
# See parameters.tf for required Parameter Store paths

variable "morning_scan_cron" {
  description = "Cron expression for morning scan (e.g., '0 9 ? * SUN-THU *')"
  type        = string
  default     = "0 9 ? * SUN-THU *"
}

variable "evening_scan_cron" {
  description = "Cron expression for evening scan (e.g., '0 18 ? * SUN-THU *')"
  type        = string
  default     = "0 18 ? * SUN-THU *"
}

variable "schedule_timezone" {
  description = "IANA timezone name for scan schedules (e.g., 'UTC', 'America/New_York'). Also passed to Lambda as SCAN_TIMEZONE for timestamp formatting."
  type        = string
  default     = "UTC"
}

variable "region" {
  description = "AWS region for resource deployment"
  type        = string
  default     = "us-east-1"
}

variable "tooling_account_id" {
  description = "AWS account ID of the account where Lambda is deployed"
  type        = string
  # No default — set TOOLING_ACCOUNT_ID in tfvars or environment
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 900 # 15 minutes
}

variable "lambda_memory" {
  description = "Lambda function memory in MB"
  type        = number
  default     = 512
}

variable "dry_run" {
  description = "Skip user DMs but send monitoring channel alerts (useful for testing)"
  type        = bool
  default     = false
}

variable "test_user_email" {
  description = "When set, redirect all DMs to this test user email (ignored when dry_run=true)"
  type        = string
  default     = ""
}

variable "enable_schedules" {
  description = "Enable EventBridge scheduled scans (disable during validation)"
  type        = bool
  default     = true
}

variable "assume_role_name" {
  description = "IAM role name to assume in target accounts. Default: OrganizationAccountAccessRole"
  type        = string
  default     = "OrganizationAccountAccessRole"
}

# Account Configuration Variables

variable "ou_id" {
  description = "AWS Organizations OU ID for this account"
  type        = string
}

variable "users_mapping" {
  description = "Map of account names to their info (id and email)"
  type = map(object({
    id    = string
    email = string
  }))
}

variable "slack_token" {
  description = "Slack bot token for sending alerts"
  type        = string
  sensitive   = true
}

variable "slack_signing_secret" {
  description = "Slack app signing secret for verifying webhook requests"
  type        = string
  sensitive   = true
}

variable "monitoring_channel" {
  description = "Slack channel for monitoring alerts"
  type        = string
  default     = "aws-alerts"
}

variable "scan_regions" {
  description = "AWS regions to scan"
  type        = list(string)
  default     = ["us-east-1"]
}

variable "scan_toggles" {
  description = "Resource types to scan"
  type = object({
    ec2           = bool
    rds           = bool
    eks           = bool
    elb           = bool
    nat           = bool
    volumes       = bool
    eip           = bool
    vpc_endpoints = bool
    lightsail     = bool
    snapshots     = bool
    rds_snapshots = bool
  })
  default = {
    ec2           = true
    rds           = true
    eks           = true
    elb           = true
    nat           = true
    volumes       = true
    eip           = true
    vpc_endpoints = true
    lightsail     = true
    snapshots     = true
    rds_snapshots = true
  }
}

# ============================================================================
# Alert Threshold Configuration
# ============================================================================

# Time-Based Thresholds (HOURS)
# ------------------------------

variable "threshold_ec2_running_hours" {
  description = "Alert threshold for running EC2 instances (hours). Default: 12 hours"
  type        = number
  default     = 12
}

variable "threshold_ec2_stopped_hours" {
  description = "Alert threshold for stopped EC2 instances (hours). Default: 672 hours (4 weeks)"
  type        = number
  default     = 672
}

variable "threshold_rds_hours" {
  description = "Alert threshold for RDS instances (hours). Default: 5 hours"
  type        = number
  default     = 5
}

variable "threshold_eks_hours" {
  description = "Alert threshold for EKS clusters (hours). Default: 12 hours"
  type        = number
  default     = 12
}

variable "threshold_eip_hours" {
  description = "Alert threshold for idle Elastic IPs (hours). Default: 2 hours"
  type        = number
  default     = 2
}

variable "threshold_lightsail_hours" {
  description = "Alert threshold for Lightsail instance age (hours). Default: 168 hours (7 days)"
  type        = number
  default     = 168
}

variable "threshold_volume_hours" {
  description = "Alert threshold for unattached EBS volume age (hours). Default: 672 hours (4 weeks)"
  type        = number
  default     = 672
}

variable "threshold_rds_snapshot_hours" {
  description = "Alert threshold for manual RDS snapshot age (hours). Default: 2160 hours (90 days)"
  type        = number
  default     = 2160
}

# Count-Based Thresholds
# ----------------------

variable "threshold_nat_gateway_count" {
  description = "Alert threshold for NAT Gateway count. Default: 0 (alerts when >0)"
  type        = number
  default     = 0
}

variable "threshold_elb_count" {
  description = "Alert threshold for Load Balancer count. Default: 0 (alerts when >0)"
  type        = number
  default     = 0
}

variable "threshold_volume_count" {
  description = "Alert threshold for unattached EBS volume count. Default: 5 (alerts when >5)"
  type        = number
  default     = 5
}

variable "threshold_eip_count" {
  description = "Alert threshold for Elastic IP count. Default: 2 (alerts when >2)"
  type        = number
  default     = 2
}

variable "threshold_vpc_endpoint_count" {
  description = "Alert threshold for VPC Endpoint count. Default: 2 (alerts when >2)"
  type        = number
  default     = 2
}

variable "threshold_lightsail_count" {
  description = "Alert threshold for Lightsail instance count. Default: 1 (alerts when >1)"
  type        = number
  default     = 1
}

variable "threshold_ebs_snapshot_count" {
  description = "Alert threshold for EBS snapshot count. Default: 10 (alerts when >10)"
  type        = number
  default     = 10
}

variable "threshold_rds_snapshot_count" {
  description = "Alert threshold for manual RDS snapshot count. Default: 5 (alerts when >5)"
  type        = number
  default     = 5
}
