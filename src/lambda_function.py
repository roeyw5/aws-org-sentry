"""AWS Lambda handler for organization account scanning."""

import os
import json
import hmac
import hashlib
import time
import base64
import boto3
from scanner.config import get_config
from scanner.accounts import get_accounts_from_mapping
from scanner.utils import assume_role, calculate_uptime
from scanner.ec2 import scan_ec2_instances
from scanner.rds import scan_rds_instances
from scanner.eks import scan_eks_clusters
from scanner.nat import scan_nat_gateways
from scanner.elb import scan_load_balancers
from scanner.volumes import scan_volumes
from scanner.eip import scan_elastic_ips
from scanner.vpc_endpoints import scan_vpc_endpoints
from scanner.lightsail import scan_lightsail_instances
from scanner.snapshots import scan_snapshots
from scanner.rds_snapshots import scan_rds_snapshots
from scanner.slack import should_alert, send_alerts, format_scan_summary, format_consolidated_monitoring_report, send_message, THRESHOLDS


def _verify_slack_signature(event, signing_secret):
    """Verify Slack request signature.

    Args:
        event: API Gateway proxy event
        signing_secret: Slack app signing secret

    Returns:
        True if signature valid, False otherwise
    """
    headers = {k.lower(): v for k, v in event.get("headers", {}).items()}
    timestamp = headers.get("x-slack-request-timestamp")
    signature = headers.get("x-slack-signature")
    body = event.get("body", "")

    # Decode base64 body if necessary
    if event.get("isBase64Encoded", False):
        body = base64.b64decode(body).decode("utf-8")

    # Validate timestamp (reject if >5 minutes old)
    if not timestamp:
        print("Request missing timestamp header")
        return False

    try:
        timestamp_int = int(timestamp)
        if abs(time.time() - timestamp_int) > 60 * 5:
            print("Request timestamp too old or missing")
            return False
    except ValueError:
        print("Invalid timestamp format")
        return False

    # Compute expected signature
    sig_basestring = f"v0:{timestamp}:{body}"
    expected_signature = "v0=" + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    # Timing-safe comparison
    return hmac.compare_digest(expected_signature, signature or "")


def _log_active_thresholds():
    """Log all active thresholds for operator visibility."""
    # Convert seconds back to hours for readability
    time_thresholds = {
        "EC2 running": THRESHOLDS["ec2_running"] // 3600,
        "EC2 stopped": THRESHOLDS["ec2_stopped"] // 3600,
        "RDS": THRESHOLDS["rds"] // 3600,
        "EKS": THRESHOLDS["eks"] // 3600,
        "EIP": THRESHOLDS["eip"] // 3600,
        "Lightsail": THRESHOLDS["lightsail"] // 3600,
        "Volume": THRESHOLDS["volume"] // 3600,
        "RDS Snapshot": THRESHOLDS["rds_snapshot"] // 3600,
    }

    count_thresholds = {
        "NAT": THRESHOLDS["nat_gateway"],
        "ELB": THRESHOLDS["elb"],
        "Volume": THRESHOLDS["volume_count"],
        "EIP": THRESHOLDS["eip_count"],
        "VPC Endpoint": THRESHOLDS["vpc_endpoint"],
        "Lightsail": THRESHOLDS["lightsail_count"],
        "EBS Snapshot": THRESHOLDS["ebs_snapshot"],
        "RDS Snapshot": THRESHOLDS["rds_snapshot_count"],
    }

    # Log grouped by type
    time_str = ", ".join(f"{k}={v}h" for k, v in time_thresholds.items())
    count_str = ", ".join(f"{k}>{v}" for k, v in count_thresholds.items())

    print("Using thresholds:")
    print(f"  Time: {time_str}")
    print(f"  Count: {count_str}")


def lambda_handler(event, context):
    """Lambda handler for AWS organization resource scanning.

    Args:
        event: Lambda event object (API Gateway or EventBridge)
        context: Lambda context object

    Returns:
        Summary dictionary with scan results (for scheduled scans)
        OR API Gateway response (for manual button clicks)
        Example: {'scanned': 5, 'failed': 1, 'resources_found': 12}
    """
    # Detect invocation source
    is_api_gateway = "requestContext" in event and "http" in event.get("requestContext", {})

    # Get account name early (needed for response)
    account_name = os.environ.get("ACCOUNT_NAME")
    if not account_name:
        raise ValueError("ACCOUNT_NAME environment variable is required")

    # Handle API Gateway invocations (Slack button clicks)
    if is_api_gateway:
        # Load signing secret from Parameter Store
        signing_secret_param = os.environ.get("SLACK_SIGNING_SECRET_PARAM")
        if not signing_secret_param:
            print("ERROR: SLACK_SIGNING_SECRET_PARAM not configured")
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Signing secret parameter not configured"})
            }

        try:
            ssm = boto3.client("ssm")
            response = ssm.get_parameter(Name=signing_secret_param, WithDecryption=True)
            signing_secret = response["Parameter"]["Value"]
        except Exception as e:
            print(f"ERROR: Failed to load signing secret from Parameter Store: {e}")
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Failed to load signing secret"})
            }

        # Verify Slack signature
        if not _verify_slack_signature(event, signing_secret):
            print("ERROR: Invalid Slack signature")
            return {
                "statusCode": 401,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Invalid signature"})
            }

        print("Manual scan triggered via Slack button")

        # Return immediate acknowledgment to Slack (must respond within 3 seconds)
        response_body = {"text": f"🔄 Scanning {account_name.upper()}... results will appear shortly"}

        # Continue with scan execution below...
        dry_run = True  # Force DRY_RUN for manual scans
        test_user_email = ""
    else:
        # Scheduled scan or manual invoke - respect DRY_RUN env var
        dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"
        test_user_email = os.environ.get("TEST_USER_EMAIL", "").strip()

    # Load configuration from Parameter Store
    config = get_config(account_name)
    print(f"Loaded configuration for account: {account_name}")

    # Log active thresholds
    _log_active_thresholds()

    # Get accounts from users mapping
    accounts = get_accounts_from_mapping(config.users_mapping)
    print(f"Found {len(accounts)} active accounts")

    # Scan each account
    summary = {"scanned": 0, "failed": 0, "resources_found": 0}

    # Collect monitoring data for consolidated report
    monitoring_data = []

    # Log startup mode
    if dry_run:
        print("DRY_RUN enabled: User DMs disabled, monitoring channel active")
    elif test_user_email:
        print(f"TEST_MODE enabled: All DMs redirected to {test_user_email}")

    for account in accounts:
        try:
            print(f"Scanning account: {account['name']} ({account['id']})")

            # Assume role in target account
            credentials = assume_role(account["id"])

            # Collect all resources with metadata for this account
            account_resources = []

            # Aggregate counts across all regions (NAT, ELB, Volume,
            # VPC Endpoint, Lightsail, Snapshot, RDS Snapshot)
            nat_total = 0
            elb_total = 0
            volume_total = 0
            vpc_endpoint_total = 0
            lightsail_total = 0
            snapshot_total = 0
            rds_snapshot_total = 0
            rds_snapshot_size_total_gb = 0

            for region in config.regions:
                print(f"  Scanning region: {region}")

                # EC2 scanning
                if config.scan_toggles.get("ec2", False):
                    instances = scan_ec2_instances(credentials, region)
                    for instance in instances:
                        uptime_seconds, uptime_formatted = calculate_uptime(
                            instance["launch_time"]
                        )
                        resource = {
                            "type": "ec2",
                            "id": instance["id"],
                            "name": instance["name"],
                            "instance_type": instance["type"],
                            "state": instance["state"],
                            "uptime_seconds": uptime_seconds,
                            "uptime_formatted": uptime_formatted,
                        }
                        account_resources.append(resource)
                        print(
                            f"    EC2: {instance['name']} ({instance['id']}) "
                            f"({instance['type']}) - "
                            f"{instance['state']} - {uptime_formatted}"
                        )

                # RDS scanning
                if config.scan_toggles.get("rds", False):
                    databases = scan_rds_instances(credentials, region)
                    for db in databases:
                        uptime_seconds, uptime_formatted = calculate_uptime(
                            db["create_time"]
                        )
                        resource = {
                            "type": "rds",
                            "id": db["id"],
                            "name": db["name"],
                            "instance_type": db["class"],
                            "state": "running",
                            "uptime_seconds": uptime_seconds,
                            "uptime_formatted": uptime_formatted,
                        }
                        account_resources.append(resource)
                        print(
                            f"    RDS: {db['name']} ({db['class']}) - "
                            f"{db['status']} - {uptime_formatted}"
                        )

                # EKS scanning
                if config.scan_toggles.get("eks", False):
                    clusters = scan_eks_clusters(credentials, region)
                    for cluster in clusters:
                        uptime_seconds, uptime_formatted = calculate_uptime(
                            cluster["created_at"]
                        )
                        resource = {
                            "type": "eks",
                            "id": cluster["name"],
                            "name": cluster["name"],
                            "version": cluster["version"],
                            "instance_type": "",
                            "state": cluster["status"].upper(),
                            "uptime_seconds": uptime_seconds,
                            "uptime_formatted": uptime_formatted,
                        }
                        account_resources.append(resource)
                        print(
                            f"    EKS: {cluster['name']} (v{cluster['version']}) - "
                            f"{cluster['status']} - {uptime_formatted}"
                        )

                # NAT Gateway scanning
                if config.scan_toggles.get("nat", False):
                    nat_count = scan_nat_gateways(credentials, region)
                    nat_total += nat_count
                    if nat_count > 0:
                        print(f"    NAT: {nat_count} gateways in {region}")

                # Load Balancer scanning
                if config.scan_toggles.get("elb", False):
                    elb_count = scan_load_balancers(credentials, region)
                    elb_total += elb_count
                    if elb_count > 0:
                        print(f"    ELB: {elb_count} load balancers in {region}")

                # EBS Volume scanning
                if config.scan_toggles.get("volumes", False):
                    volumes = scan_volumes(credentials, region)
                    volume_count = len(volumes)
                    volume_total += volume_count

                    # Track individual volumes for age threshold
                    for vol in volumes:
                        uptime_seconds, uptime_formatted = calculate_uptime(vol["created_at"])
                        resource = {
                            "type": "volume",
                            "id": vol["id"],
                            "size_gb": vol["size_gb"],
                            "region": region,
                            "uptime_seconds": uptime_seconds,
                            "uptime_formatted": uptime_formatted,
                        }
                        account_resources.append(resource)
                        print(
                            f"    VOL: {vol['id']} ({vol['size_gb']}GB) - "
                            f"idle for {uptime_formatted}"
                        )

                # Elastic IP scanning
                if config.scan_toggles.get("eip", False):
                    eips = scan_elastic_ips(credentials, region)
                    for eip in eips:
                        uptime_seconds, uptime_formatted = calculate_uptime(
                            eip["allocation_time"]
                        )
                        resource = {
                            "type": "eip",
                            "id": eip["id"],
                            "public_ip": eip["public_ip"],
                            "state": "unattached",
                            "uptime_seconds": uptime_seconds,
                            "uptime_formatted": uptime_formatted,
                        }
                        account_resources.append(resource)
                        print(
                            f"    EIP: {eip['public_ip']} unattached - "
                            f"{uptime_formatted}"
                        )

                # VPC Endpoint scanning
                if config.scan_toggles.get("vpc_endpoints", False):
                    result = scan_vpc_endpoints(credentials, region)
                    vpc_endpoint_total += result["count"]
                    if result["count"] > 0:
                        services = ", ".join(result["service_names"])
                        print(
                            f"    VPC Endpoints: {result['count']} interface "
                            f"endpoints ({services}) in {region}"
                        )

                # Lightsail scanning
                if config.scan_toggles.get("lightsail", False):
                    instances = scan_lightsail_instances(credentials, region)
                    lightsail_total += len(instances)
                    for instance in instances:
                        uptime_seconds, uptime_formatted = calculate_uptime(
                            instance["created_at"]
                        )
                        resource = {
                            "type": "lightsail",
                            "id": instance["name"],
                            "name": instance["name"],
                            "bundle_id": instance["bundle_id"],
                            "state": instance["state"],
                            "uptime_seconds": uptime_seconds,
                            "uptime_formatted": uptime_formatted,
                        }
                        account_resources.append(resource)
                        print(
                            f"    Lightsail: {instance['name']} ({instance['bundle_id']}) - "
                            f"{instance['state']} - {uptime_formatted}"
                        )

                # EBS Snapshot scanning
                if config.scan_toggles.get("snapshots", False):
                    snapshots = scan_snapshots(credentials, region)
                    snapshot_count = len(snapshots)
                    snapshot_total += snapshot_count
                    if snapshot_count > 0:
                        print(f"    Snapshots: {snapshot_count} snapshots in {region}")

                # RDS Snapshot scanning
                if config.scan_toggles.get("rds_snapshots", False):
                    rds_snapshots = scan_rds_snapshots(credentials, region)
                    rds_snapshot_total += len(rds_snapshots)

                    # Track individual snapshots for age threshold
                    for snapshot in rds_snapshots:
                        uptime_seconds, uptime_formatted = calculate_uptime(snapshot["created_at"])
                        rds_snapshot_size_total_gb += snapshot["size_gb"]

                        resource = {
                            "type": "rds_snapshot",
                            "id": snapshot["id"],
                            "size_gb": snapshot["size_gb"],
                            "region": region,
                            "uptime_seconds": uptime_seconds,
                            "uptime_formatted": uptime_formatted,
                        }
                        account_resources.append(resource)
                        print(
                            f"    RDS Snapshot: {snapshot['id']} "
                            f"({snapshot['size_gb']}GB) - {uptime_formatted}"
                        )

                    if len(rds_snapshots) > 0:
                        # Find oldest snapshot for logging
                        oldest = max(
                            rds_snapshots,
                            key=lambda s: calculate_uptime(s["created_at"])[0],
                        )
                        oldest_age = calculate_uptime(oldest["created_at"])[1]
                        total_size = sum(s["size_gb"] for s in rds_snapshots)
                        print(
                            f"    RDS Snapshots: {len(rds_snapshots)} manual in "
                            f"{region} (oldest: {oldest_age}, {total_size}GB)"
                        )

            # Check thresholds and send alerts
            alertable = [r for r in account_resources if should_alert(r)]

            # Check EIP count threshold (>2)
            eip_count = len([r for r in account_resources if r["type"] == "eip"])

            # Log filtering results
            print(
                f"  Account scan complete: {len(account_resources)} resources found, "
                f"{len(alertable)} exceeded thresholds"
            )

            # Send alerts if alertable resources OR counts exceed thresholds
            if (
                alertable
                or nat_total > THRESHOLDS["nat_gateway"]
                or elb_total > THRESHOLDS["elb"]
                or volume_total > THRESHOLDS["volume_count"]
                or eip_count > THRESHOLDS["eip_count"]
                or vpc_endpoint_total > THRESHOLDS["vpc_endpoint"]
                or lightsail_total > THRESHOLDS["lightsail_count"]
                or snapshot_total > THRESHOLDS["ebs_snapshot"]
                or rds_snapshot_total > THRESHOLDS["rds_snapshot_count"]
            ):
                user_data = config.users_mapping.get(account["name"])
                if user_data:
                    recipient_email = user_data.get("email")
                    account_monitoring_data = send_alerts(
                        account["name"],
                        account["id"],
                        recipient_email,
                        alertable,
                        config.slack_token,
                        config.monitoring_channel,
                        dry_run,
                        (
                            nat_total
                            if nat_total > THRESHOLDS["nat_gateway"]
                            else 0
                        ),
                        elb_total if elb_total > THRESHOLDS["elb"] else 0,
                        (
                            volume_total
                            if volume_total > THRESHOLDS["volume_count"]
                            else 0
                        ),
                        (
                            eip_count
                            if eip_count > THRESHOLDS["eip_count"]
                            else 0
                        ),
                        (
                            vpc_endpoint_total
                            if vpc_endpoint_total > THRESHOLDS["vpc_endpoint"]
                            else 0
                        ),
                        (
                            lightsail_total
                            if lightsail_total > THRESHOLDS["lightsail_count"]
                            else 0
                        ),
                        (
                            snapshot_total
                            if snapshot_total > THRESHOLDS["ebs_snapshot"]
                            else 0
                        ),
                        (
                            rds_snapshot_total
                            if rds_snapshot_total
                            > THRESHOLDS["rds_snapshot_count"]
                            else 0
                        ),
                        rds_snapshot_size_total_gb,
                        test_user_email,
                    )
                    monitoring_data.append(account_monitoring_data)

            summary["scanned"] += 1
            summary["resources_found"] += len(account_resources)

        except Exception as e:
            print(f"Error scanning {account['name']}: {e}")
            summary["failed"] += 1

    # Print summary
    print("\nScan complete:")
    print(f"  Accounts scanned: {summary['scanned']}")
    print(f"  Accounts failed: {summary['failed']}")
    print(f"  Total resources found: {summary['resources_found']}")

    # Send consolidated monitoring report and summary only if there are alerts
    if monitoring_data:
        print(f"\nSending consolidated monitoring report: {len(monitoring_data)} accounts with alerts")
        monitoring_blocks = format_consolidated_monitoring_report(
            config.account_name.upper(), monitoring_data
        )
        send_message(config.monitoring_channel, monitoring_blocks, config.slack_token)

        summary_blocks = format_scan_summary(
            config.account_name.upper(),
            summary["scanned"],
            summary["failed"],
            summary["resources_found"],
        )
        send_message(config.monitoring_channel, summary_blocks, config.slack_token)
    else:
        print("\nNo alerts to report - skipping Slack messages")

    # Return response based on invocation source
    if is_api_gateway:
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(response_body)
        }
    else:
        return summary
