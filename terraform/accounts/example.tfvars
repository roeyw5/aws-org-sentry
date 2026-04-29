# Example Account Configuration
# Copy this file to accounts/<account-name>.tfvars and customize.
# Keep your real account tfvars files OUT of version control — they contain secrets.

account_name = "staging"
ou_id        = "ou-xxxx-xxxxxxxx"

# Tooling account where the Lambda is deployed (12-digit account ID)
tooling_account_id = "123456789012"

# Map of account names to their info — Terraform writes this to Parameter Store
users_mapping = {
  "John.Doe" = {
    id    = "123456789012"
    email = "john.doe@example.com"
  }
  "Jane.Smith" = {
    id    = "234567890123"
    email = "jane.smith@example.com"
  }
}

slack_token          = "xoxb-YOUR-SLACK-TOKEN"
slack_signing_secret = "PLACEHOLDER" # Optional: only needed for webhook verification
monitoring_channel   = "aws-alerts"

# Scan schedule (cron expressions evaluated in `schedule_timezone`)
schedule_timezone = "UTC"
morning_scan_cron = "0 9 ? * SUN-THU *"
evening_scan_cron = "0 18 ? * SUN-THU *"

# Testing configuration — start with safe defaults
dry_run          = true  # Monitoring channel only, no DMs
test_user_email  = ""    # Set to your email for pre-production DM testing
enable_schedules = false # Disabled until validation complete

# Testing workflow:
# 1. Initial deploy: dry_run=true, test_user_email="", enable_schedules=false
# -> Monitoring channel only, manual invocation
# 2. Test user mode: dry_run=false, test_user_email="your@email.com", enable_schedules=false
# -> You receive all DMs (with TEST MODE prefix), manual invocation
# 3. Production:    dry_run=false, test_user_email="",                 enable_schedules=true
# -> Real recipients receive DMs, automatic schedules enabled
