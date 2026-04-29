resource "aws_lambda_function" "scanner" {
  function_name = "aws-scanner-${var.account_name}"
  role          = aws_iam_role.lambda.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.11"

  filename         = "${path.module}/../../../lambda-package.zip"
  source_code_hash = filebase64sha256("${path.module}/../../../lambda-package.zip")

  memory_size = var.lambda_memory
  timeout     = var.lambda_timeout

  environment {
    variables = {
      DRY_RUN          = var.dry_run ? "true" : "false"
      TEST_USER_EMAIL  = var.test_user_email
      ACCOUNT_NAME     = var.account_name
      ASSUME_ROLE_NAME = var.assume_role_name
      SCAN_TIMEZONE    = var.schedule_timezone

      # Slack Signing Secret (loaded from Parameter Store, reference only)
      SLACK_SIGNING_SECRET_PARAM = aws_ssm_parameter.slack_signing_secret.name

      # Time-Based Thresholds (HOURS)
      THRESHOLD_EC2_RUNNING_HOURS  = var.threshold_ec2_running_hours
      THRESHOLD_EC2_STOPPED_HOURS  = var.threshold_ec2_stopped_hours
      THRESHOLD_RDS_HOURS          = var.threshold_rds_hours
      THRESHOLD_EKS_HOURS          = var.threshold_eks_hours
      THRESHOLD_EIP_HOURS          = var.threshold_eip_hours
      THRESHOLD_LIGHTSAIL_HOURS    = var.threshold_lightsail_hours
      THRESHOLD_VOLUME_HOURS       = var.threshold_volume_hours
      THRESHOLD_RDS_SNAPSHOT_HOURS = var.threshold_rds_snapshot_hours

      # Count-Based Thresholds
      THRESHOLD_NAT_GATEWAY_COUNT  = var.threshold_nat_gateway_count
      THRESHOLD_ELB_COUNT          = var.threshold_elb_count
      THRESHOLD_VOLUME_COUNT       = var.threshold_volume_count
      THRESHOLD_EIP_COUNT          = var.threshold_eip_count
      THRESHOLD_VPC_ENDPOINT_COUNT = var.threshold_vpc_endpoint_count
      THRESHOLD_LIGHTSAIL_COUNT    = var.threshold_lightsail_count
      THRESHOLD_EBS_SNAPSHOT_COUNT = var.threshold_ebs_snapshot_count
      THRESHOLD_RDS_SNAPSHOT_COUNT = var.threshold_rds_snapshot_count
    }
  }

  tags = {
    Account = var.account_name
  }
}

# CloudWatch Logs for debugging and troubleshooting
# 7-day retention prevents unbounded growth while allowing recent debugging
# Slack notifications remain the primary production visibility mechanism
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/aws-scanner-${var.account_name}"
  retention_in_days = 7

  tags = {
    Account = var.account_name
  }
}
