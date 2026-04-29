# Alert Threshold Configuration Reference

This document lists all configurable alert thresholds for the AWS Organization Scanner.

## How to Use

Add any of these variables to your account `tfvars` file to override defaults:

```hcl
# Example: Make EC2 alerts more strict
threshold_ec2_running_hours = 6  # Alert after 6 hours instead of default 12h
```

## Time-Based Thresholds

All time thresholds are specified in **HOURS**.

| Variable | Default | Description |
|----------|---------|-------------|
| `threshold_ec2_running_hours` | 12 | Alert if EC2 instance running > N hours |
| `threshold_ec2_stopped_hours` | 36 | Alert if EC2 instance stopped > N hours |
| `threshold_rds_hours` | 24 | Alert if RDS database running > N hours |
| `threshold_eks_hours` | 24 | Alert if EKS cluster active > N hours |
| `threshold_eip_hours` | 2 | Alert if Elastic IP unattached > N hours |
| `threshold_lightsail_hours` | 168 | Alert if Lightsail instance > N hours (7 days) |
| `threshold_volume_hours` | 168 | Alert if EBS volume idle > N hours (7 days) |
| `threshold_rds_snapshot_hours` | 2160 | Alert if RDS snapshot > N hours (90 days) |

## Count-Based Thresholds

All count thresholds alert when the count **exceeds** the threshold (>).

| Variable | Default | Description |
|----------|---------|-------------|
| `threshold_nat_gateway_count` | 1 | Alert if >1 NAT Gateway |
| `threshold_elb_count` | 1 | Alert if >1 Load Balancer (any type) |
| `threshold_volume_count` | 5 | Alert if >5 unattached EBS volumes |
| `threshold_eip_count` | 2 | Alert if >2 unattached Elastic IPs |
| `threshold_vpc_endpoint_count` | 2 | Alert if >2 interface VPC endpoints |
| `threshold_lightsail_count` | 1 | Alert if >1 Lightsail instance |
| `threshold_ebs_snapshot_count` | 20 | Alert if >20 EBS snapshots |
| `threshold_rds_snapshot_count` | 10 | Alert if >10 manual RDS snapshots |

## Dual-Threshold Resources

Some resources have **both** time AND count thresholds. An alert is triggered if **either** threshold is exceeded:

- **EBS Volumes**: Age > 168h (7d) **OR** Count > 5
- **Elastic IPs**: Unattached > 2h **OR** Count > 2
- **Lightsail**: Age > 168h (7d) **OR** Count > 1
- **RDS Snapshots**: Age > 2160h (90d) **OR** Count > 10

## Examples

### Strict Account Example
```hcl
# Aggressive alerts for short-lived environments
threshold_ec2_running_hours = 6    # Alert after 6 hours
threshold_volume_hours      = 48   # Alert after 2 days
threshold_volume_count      = 3    # Alert if >3 volumes
threshold_elb_count         = 0    # Alert on ANY load balancer
```

### Relaxed Account Example
```hcl
# Lenient thresholds for self-paced learning
threshold_ec2_running_hours = 48   # Alert after 2 days
threshold_volume_hours      = 336  # Alert after 14 days
threshold_volume_count      = 10   # Alert if >10 volumes
```

### Production Defaults
```hcl
# Use defaults - no need to specify anything
# All thresholds will use the values shown in the tables above
```

## Testing Thresholds

To test custom thresholds:

1. Set `test_user_email` in tfvars to redirect alerts to yourself
2. Set custom thresholds
3. Deploy: `terraform apply -var-file="accounts/<account_name>.tfvars"`
4. Invoke Lambda manually: `aws lambda invoke ...`
5. Check CloudWatch logs for "Using thresholds:" to verify values
6. Verify Slack alerts reflect new thresholds

## Implementation Details

- **Defaults**: Defined in `terraform/modules/account-scanner/variables.tf`
- **Lambda Environment**: Passed as `THRESHOLD_*` environment variables
- **Python Code**: Loaded in `src/scanner/slack.py` via `_get_thresholds()`
- **Validation**: Invalid values (negative, non-numeric) fall back to defaults with warnings in CloudWatch
