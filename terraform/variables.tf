# Root-level Workspace Input Variables
# These variables are provided via .tfvars files for each workspace

variable "account_name" {
  description = "Name of the account (e.g., dev, staging, prod)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.account_name))
    error_message = "Account name must contain only lowercase letters, numbers, and hyphens"
  }
}

variable "ou_id" {
  description = "AWS Organizations OU ID for this account"
  type        = string
}

variable "users_mapping" {
  description = "Map of account names to their info"
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
  default     = ""
  sensitive   = true
}

variable "monitoring_channel" {
  description = "Slack channel for monitoring alerts"
  type        = string
  default     = "aws-alerts"
}

variable "morning_scan_cron" {
  description = "Cron expression for morning scan"
  type        = string
  default     = "0 9 ? * SUN-THU *"
}

variable "evening_scan_cron" {
  description = "Cron expression for evening scan"
  type        = string
  default     = "0 18 ? * SUN-THU *"
}

variable "schedule_timezone" {
  description = "IANA timezone for EventBridge scan schedules (e.g., 'UTC', 'America/New_York')"
  type        = string
  default     = "UTC"
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
  description = "IAM role name to assume in target accounts"
  type        = string
  default     = "OrganizationAccountAccessRole"
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
# Optional Alert Threshold Overrides
# ============================================================================
# These variables allow per-account customization of alert thresholds.
# If not specified in tfvars, module defaults are used.

variable "threshold_ec2_running_hours" {
  description = "Alert threshold for running EC2 instances (hours). Defaults to module default: 12"
  type        = number
  default     = null
}

variable "threshold_ec2_stopped_hours" {
  description = "Alert threshold for stopped EC2 instances (hours). Defaults to module default: 672 (4 weeks)"
  type        = number
  default     = null
}

variable "threshold_rds_hours" {
  description = "Alert threshold for RDS instances (hours). Defaults to module default: 5"
  type        = number
  default     = null
}

variable "threshold_eks_hours" {
  description = "Alert threshold for EKS clusters (hours). Defaults to module default: 12"
  type        = number
  default     = null
}

variable "threshold_eip_hours" {
  description = "Alert threshold for idle Elastic IPs (hours). Defaults to module default: 2"
  type        = number
  default     = null
}

variable "threshold_lightsail_hours" {
  description = "Alert threshold for Lightsail instance age (hours). Defaults to module default: 168 (7 days)"
  type        = number
  default     = null
}

variable "threshold_volume_hours" {
  description = "Alert threshold for unattached EBS volume age (hours). Defaults to module default: 672 (4 weeks)"
  type        = number
  default     = null
}

variable "threshold_rds_snapshot_hours" {
  description = "Alert threshold for manual RDS snapshot age (hours). Defaults to module default: 2160 (90 days)"
  type        = number
  default     = null
}

variable "threshold_nat_gateway_count" {
  description = "Alert threshold for NAT Gateway count. Defaults to module default: 0 (alerts when >0)"
  type        = number
  default     = null
}

variable "threshold_elb_count" {
  description = "Alert threshold for Load Balancer count. Defaults to module default: 0 (alerts when >0)"
  type        = number
  default     = null
}

variable "threshold_volume_count" {
  description = "Alert threshold for unattached EBS volume count. Defaults to module default: 5"
  type        = number
  default     = null
}

variable "threshold_eip_count" {
  description = "Alert threshold for Elastic IP count. Defaults to module default: 2"
  type        = number
  default     = null
}

variable "threshold_vpc_endpoint_count" {
  description = "Alert threshold for VPC Endpoint count. Defaults to module default: 2 (alerts when >2)"
  type        = number
  default     = null
}

variable "threshold_lightsail_count" {
  description = "Alert threshold for Lightsail instance count. Defaults to module default: 1"
  type        = number
  default     = null
}

variable "threshold_ebs_snapshot_count" {
  description = "Alert threshold for EBS snapshot count. Defaults to module default: 10 (alerts when >10)"
  type        = number
  default     = null
}

variable "threshold_rds_snapshot_count" {
  description = "Alert threshold for manual RDS snapshot count. Defaults to module default: 5 (alerts when >5)"
  type        = number
  default     = null
}
