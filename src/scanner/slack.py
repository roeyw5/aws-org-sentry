"""Slack API integration for per-account alerts and monitoring."""

import os
import time
import requests
import pytz
from datetime import datetime
from typing import List, Dict, Optional


# User ID cache to minimize API calls
_user_cache = {}


def find_slack_user(email: str, token: str) -> Optional[str]:
    """Find Slack user ID by email with caching.

    Args:
        email: User email address
        token: Slack bot token

    Returns:
        Slack user ID or None if not found
    """
    if email in _user_cache:
        return _user_cache[email]

    response = requests.get(
        "https://slack.com/api/users.lookupByEmail",
        headers={"Authorization": f"Bearer {token}"},
        params={"email": email},
    )
    data = response.json()

    if data.get("ok"):
        user_id = data["user"]["id"]
        _user_cache[email] = user_id
        return user_id

    return None


def open_dm_channel(user_id: str, token: str) -> Optional[str]:
    """Open DM channel with user.

    Args:
        user_id: Slack user ID
        token: Slack bot token

    Returns:
        Channel ID or None if failed
    """
    response = requests.post(
        "https://slack.com/api/conversations.open",
        headers={"Authorization": f"Bearer {token}"},
        json={"users": user_id},
    )
    data = response.json()

    if data.get("ok"):
        return data["channel"]["id"]

    return None


def send_message(
    channel: str, blocks: List[Dict], token: str, max_retries: int = 3
) -> bool:
    """Send message with exponential backoff retry.

    Args:
        channel: Slack channel ID
        blocks: Slack Block Kit blocks
        token: Slack bot token
        max_retries: Maximum retry attempts for rate limiting

    Returns:
        True if message sent successfully, False otherwise
    """
    for attempt in range(max_retries):
        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {token}"},
            json={"channel": channel, "blocks": blocks},
        )
        data = response.json()

        if data.get("ok"):
            return True

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 2**attempt))
            time.sleep(retry_after)
            continue

        return False

    return False


def _is_multi_region(resources: List[Dict]) -> bool:
    """Detect if account has resources in multiple regions.

    Args:
        resources: List of resource dictionaries with optional region field

    Returns:
        True if resources span more than one region
    """
    regions = {r.get("region") for r in resources if r.get("region")}
    return len(regions) > 1


def format_account_dm(
    account_name: str,
    resources: List[Dict],
    nat_count: int = 0,
    elb_count: int = 0,
    volume_count: int = 0,
    eip_count: int = 0,
    vpc_endpoint_count: int = 0,
    lightsail_count: int = 0,
    snapshot_count: int = 0,
    rds_snapshot_count: int = 0,
    rds_snapshot_size_gb: int = 0,
) -> List[Dict]:
    """Format per-account DM with resources.

    Args:
        account_name: AWS account name
        resources: List of resource dictionaries with type, state, id,
                   instance_type, uptime_seconds, uptime_formatted
        nat_count: Count of NAT Gateways (only shown if > 1)
        elb_count: Count of Load Balancers (only shown if > 1)
        volume_count: Count of unattached EBS volumes (only shown if > 5)
        eip_count: Count of unattached Elastic IPs (only shown if > 2)
        vpc_endpoint_count: Count of interface VPC endpoints (only shown if > 2)
        lightsail_count: Count of Lightsail instances (only shown if > 1)
        snapshot_count: Count of EBS snapshots (only shown if > 10)
        rds_snapshot_count: Count of RDS manual snapshots (only shown if > 10)
        rds_snapshot_size_gb: Total size in GB of RDS snapshots

    Returns:
        Slack Block Kit blocks
    """
    blocks = []

    # Detect if multi-region account
    multi_region = _is_multi_region(resources)

    # Universal header shown for all alerts
    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*AWS Resources Requiring Attention*",
            },
        }
    )

    # Separate resources by type and state
    running_ec2 = [
        r for r in resources if r["type"] == "ec2" and r["state"] == "running"
    ]
    stopped_ec2 = [
        r for r in resources if r["type"] == "ec2" and r["state"] == "stopped"
    ]
    rds = [r for r in resources if r["type"] == "rds"]
    eks = [r for r in resources if r["type"] == "eks"]
    eip = [r for r in resources if r["type"] == "eip"]
    lightsail = [r for r in resources if r["type"] == "lightsail"]
    volumes = [r for r in resources if r["type"] == "volume"]
    rds_snapshots = [r for r in resources if r["type"] == "rds_snapshot"]

    # Running EC2 instances
    if running_ec2:
        lines = ["*Running Instances:*"]
        for instance in running_ec2:
            uptime_hours = instance["uptime_seconds"] / 3600
            emoji = " 😱" if uptime_hours > 12 else ""
            name = instance.get("name", "No Name")
            lines.append(
                f"• {name} ({instance['instance_type']}) - "
                f"Running for {instance['uptime_formatted']}{emoji}"
            )
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}}
        )

    # Stopped EC2 instances
    if stopped_ec2:
        lines = ["🛑 *Stopped Instances:*"]
        for instance in stopped_ec2:
            name = instance.get("name", "No Name")
            lines.append(
                f"• {name} ({instance['instance_type']}) - "
                f"Stopped for {instance['uptime_formatted']}"
            )
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}}
        )

    # RDS databases
    if rds:
        lines = ["📊 *RDS Databases:*"]
        for db in rds:
            name = db.get("name", db["id"])
            lines.append(
                f"• {name} ({db['instance_type']}) - "
                f"Running for {db['uptime_formatted']}"
            )
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}}
        )

    # EKS clusters
    if eks:
        lines = ["☸️ *EKS Clusters:*"]
        for cluster in eks:
            name = cluster.get("name", cluster["id"])
            version = cluster.get("version", "unknown")
            lines.append(
                f"• {name} (v{version}) - "
                f"Running for {cluster['uptime_formatted']}"
            )
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}}
        )

    # Elastic IPs (individual items exceeding time threshold)
    if eip:
        lines = ["🌐 *Elastic IPs:*"]
        for ip in eip:
            public_ip = ip.get("public_ip", ip["id"])
            region_suffix = f" in {ip.get('region', 'unknown')}" if multi_region else ""
            lines.append(
                f"• {public_ip} - "
                f"Unattached for {ip['uptime_formatted']}{region_suffix}"
            )
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}}
        )

    # Lightsail instances (individual items exceeding time threshold)
    if lightsail:
        lines = ["💡 *Lightsail Instances:*"]
        for instance in lightsail:
            name = instance.get("name", instance["id"])
            bundle = instance.get("bundle_id", "unknown")
            state = instance.get("state", "unknown")
            region_suffix = f" in {instance.get('region', 'unknown')}" if multi_region else ""
            lines.append(
                f"• {name} ({bundle}) - {state} - "
                f"age: {instance['uptime_formatted']}{region_suffix}"
            )
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}}
        )

    # EBS Volumes (individual items exceeding age threshold)
    if volumes:
        lines = ["💾 *EBS Volumes:*"]
        for vol in volumes:
            vol_id = vol["id"]
            size_gb = vol.get("size_gb", 0)
            region = vol.get("region", "unknown")
            region_suffix = f" in {region}" if multi_region else ""
            lines.append(
                f"• {vol_id} idle {vol['uptime_formatted']} "
                f"({size_gb}GB){region_suffix}"
            )
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}}
        )

    # RDS Snapshots (individual items exceeding age threshold)
    if rds_snapshots:
        lines = ["💿 *RDS Snapshots:*"]
        for snapshot in rds_snapshots:
            snapshot_id = snapshot["id"]
            size_gb = snapshot.get("size_gb", 0)
            lines.append(
                f"• {snapshot_id} is {snapshot['uptime_formatted']} old "
                f"({size_gb}GB, threshold: >90d)"
            )
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}}
        )

    # NAT/ELB/Volume/EIP count/VPC Endpoint/Lightsail/Snapshot/RDS Snapshot
    # if counts exceed thresholds
    if (
        nat_count > THRESHOLDS["nat_gateway"]
        or elb_count > THRESHOLDS["elb"]
        or volume_count > THRESHOLDS["volume_count"]
        or eip_count > THRESHOLDS["eip_count"]
        or vpc_endpoint_count > THRESHOLDS["vpc_endpoint"]
        or lightsail_count > THRESHOLDS["lightsail_count"]
        or snapshot_count > THRESHOLDS["ebs_snapshot"]
        or rds_snapshot_count > THRESHOLDS["rds_snapshot_count"]
    ):
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Resource Counts:*"},
            }
        )

        warnings = []
        if nat_count > THRESHOLDS["nat_gateway"]:
            warnings.append(f"• NAT Gateways: {nat_count} active")

        if elb_count > THRESHOLDS["elb"]:
            warnings.append(f"• Load Balancers: {elb_count} active")

        if volume_count > THRESHOLDS["volume_count"]:
            warnings.append(f"• Unattached EBS Volumes: {volume_count} volumes")

        if eip_count > THRESHOLDS["eip_count"]:
            warnings.append(f"• Elastic IPs: {eip_count} unattached")

        if vpc_endpoint_count > THRESHOLDS["vpc_endpoint"]:
            warnings.append(f"• VPC Endpoints: {vpc_endpoint_count} interface endpoints")

        if lightsail_count > THRESHOLDS["lightsail_count"]:
            warnings.append(f"• Lightsail: {lightsail_count} instances detected")

        if snapshot_count > THRESHOLDS["ebs_snapshot"]:
            warnings.append(f"• EBS Snapshots: {snapshot_count} snapshots")

        if rds_snapshot_count > THRESHOLDS["rds_snapshot_count"]:
            warnings.append(
                f"• RDS Snapshots: {rds_snapshot_count} manual (Total: {rds_snapshot_size_gb}GB)"
            )

        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(warnings)}}
        )

    # Add concise footer
    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "_Review resources to avoid charges._",
            },
        }
    )

    return blocks


def format_monitoring_alert(
    account_name: str,
    account_id: str,
    recipient_email: str,
    resources: List[Dict],
    nat_count: int = 0,
    elb_count: int = 0,
    volume_count: int = 0,
    eip_count: int = 0,
    vpc_endpoint_count: int = 0,
    lightsail_count: int = 0,
    snapshot_count: int = 0,
    rds_snapshot_count: int = 0,
    rds_snapshot_size_gb: int = 0,
) -> List[Dict]:
    """Format monitoring channel alert - matches bash script detail level.

    Args:
        account_name: AWS account name
        account_id: AWS account ID
        recipient_email: User email address
        resources: List of resource dictionaries
        nat_count: Count of NAT Gateways (only shown if > 1)
        elb_count: Count of Load Balancers (only shown if > 1)
        volume_count: Count of unattached EBS volumes (only shown if > 5)
        eip_count: Count of unattached Elastic IPs (only shown if > 2)
        vpc_endpoint_count: Count of interface VPC endpoints (only shown if > 2)
        lightsail_count: Count of Lightsail instances (only shown if > 1)
        snapshot_count: Count of EBS snapshots (only shown if > 10)
        rds_snapshot_count: Count of RDS manual snapshots (only shown if > 10)
        rds_snapshot_size_gb: Total size in GB of RDS snapshots

    Returns:
        Slack Block Kit blocks
    """
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"🚨 *Active Resources Found*\n"
                    f"User: {account_name}\n"
                    f"Account: {account_id}"
                ),
            },
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": "*Resources:*"}},
    ]

    # Build detailed resource list
    resource_lines = []
    for resource in resources:
        if resource["type"] == "ec2":
            name = resource.get("name", "No Name")
            instance_type = resource["instance_type"]
            state = resource["state"]
            uptime = resource["uptime_formatted"]
            warning = (
                " ⚠️"
                if resource["uptime_seconds"] / 3600 > 12 and state == "running"
                else ""
            )
            resource_lines.append(
                f"• EC2: {name} ({instance_type}) - {state} (uptime: {uptime}){warning}"
            )

        elif resource["type"] == "rds":
            name = resource.get("name", resource["id"])
            instance_class = resource["instance_type"]
            uptime = resource["uptime_formatted"]
            resource_lines.append(
                f"• RDS: {name} ({instance_class}) - running (uptime: {uptime})"
            )

        elif resource["type"] == "eks":
            name = resource.get("name", resource["id"])
            version = resource.get("version", "unknown")
            state = resource.get("state", "ACTIVE")
            uptime = resource["uptime_formatted"]
            resource_lines.append(
                f"• EKS: {name} (v{version}) - {state} (uptime: {uptime})"
            )

        elif resource["type"] == "eip":
            public_ip = resource.get("public_ip", resource["id"])
            uptime = resource["uptime_formatted"]
            resource_lines.append(
                f"• EIP: {public_ip} - unattached (uptime: {uptime})"
            )

        elif resource["type"] == "lightsail":
            name = resource.get("name", resource["id"])
            bundle = resource.get("bundle_id", "unknown")
            state = resource.get("state", "unknown")
            uptime = resource["uptime_formatted"]
            resource_lines.append(
                f"• Lightsail: {name} ({bundle}) - {state} (age: {uptime})"
            )

        elif resource["type"] == "volume":
            vol_id = resource["id"]
            size_gb = resource.get("size_gb", 0)
            region = resource.get("region", "unknown")
            uptime = resource["uptime_formatted"]
            resource_lines.append(
                f"• Volume: {vol_id} ({size_gb}GB) - idle for {uptime} in {region}"
            )

        elif resource["type"] == "rds_snapshot":
            snapshot_id = resource["id"]
            size_gb = resource.get("size_gb", 0)
            uptime = resource["uptime_formatted"]
            resource_lines.append(
                f"• RDS Snapshot: {snapshot_id} ({size_gb}GB) - {uptime} old"
            )

    # Add resource count warnings if counts exceed thresholds
    # (NAT/ELB/Volume/EIP/VPC Endpoint/Lightsail/Snapshot/RDS Snapshot)
    if nat_count > THRESHOLDS["nat_gateway"]:
        resource_lines.append(f"⚠️ Active NAT Gateways: {nat_count}")

    if elb_count > THRESHOLDS["elb"]:
        resource_lines.append(f"⚠️ Active Load Balancers: {elb_count}")

    if volume_count > THRESHOLDS["volume_count"]:
        resource_lines.append(f"⚠️ Unattached EBS Volumes: {volume_count}")

    if eip_count > THRESHOLDS["eip_count"]:
        resource_lines.append(f"⚠️ Unattached Elastic IPs: {eip_count}")

    if vpc_endpoint_count > THRESHOLDS["vpc_endpoint"]:
        resource_lines.append(f"⚠️ Interface VPC Endpoints: {vpc_endpoint_count}")

    if lightsail_count > THRESHOLDS["lightsail_count"]:
        resource_lines.append(f"⚠️ Lightsail Instances: {lightsail_count}")

    if snapshot_count > THRESHOLDS["ebs_snapshot"]:
        resource_lines.append(f"⚠️ EBS Snapshots: {snapshot_count}")

    if rds_snapshot_count > THRESHOLDS["rds_snapshot_count"]:
        resource_lines.append(
            f"⚠️ RDS Snapshots: {rds_snapshot_count} manual "
            f"({rds_snapshot_size_gb}GB)"
        )

    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(resource_lines[:MAX_RESOURCES_IN_MONITORING_ALERT]),
            },
        }
    )

    return blocks


def _get_local_timestamp() -> str:
    """Get current timestamp in the configured timezone.

    Reads the timezone from the SCAN_TIMEZONE env var (defaults to UTC).
    Returns a formatted timestamp string like "2025-10-22 18:00 UTC".
    """
    tz_name = os.environ.get("SCAN_TIMEZONE", "UTC")
    try:
        local_tz = pytz.timezone(tz_name)
    except pytz.UnknownTimeZoneError:
        local_tz = pytz.utc
        tz_name = "UTC"
    now_utc = datetime.now(pytz.utc)
    now_local = now_utc.astimezone(local_tz)
    return now_local.strftime(f"%Y-%m-%d %H:%M {tz_name}")


def format_consolidated_monitoring_report(
    account_name: str, monitoring_data: List[Dict]
) -> List[Dict]:
    """Format consolidated monitoring report with all accounts in a single message.

    Args:
        account_name: Account name (e.g., dev, staging)
        monitoring_data: List of dicts with keys:
            - user_name: str
            - account_id: str
            - high_cost_resources: List[Dict] (EC2 running, RDS, EKS, NAT, ELB, Lightsail)
            - low_cost_counts: Dict[str, int] (volumes, snapshots, stopped_ec2, eips, vpc_endpoints, rds_snapshots)

    Returns:
        Slack Block Kit blocks for consolidated report
    """
    if not monitoring_data:
        # Empty scan case
        text = f"✅ *{account_name} Alert Report* • {_get_local_timestamp()}\nNo active resources found"
        return [{"type": "section", "text": {"type": "mrkdwn", "text": text}}]

    # Sort accounts alphabetically
    sorted_data = sorted(monitoring_data, key=lambda x: x["user_name"])

    # Calculate summary statistics
    total_users = len(sorted_data)
    resource_totals = {
        "ec2_running": 0,
        "ec2_stopped": 0,
        "rds": 0,
        "eks": 0,
        "volumes": 0,
        "snapshots": 0,
        "eips": 0,
        "nat": 0,
        "elb": 0,
        "lightsail": 0,
    }

    for user in sorted_data:
        # Count high-cost resources
        for resource in user["high_cost_resources"]:
            if resource["type"] == "ec2":
                if resource["state"].lower() == "running":
                    resource_totals["ec2_running"] += 1
                else:
                    resource_totals["ec2_stopped"] += 1
            elif resource["type"] == "rds":
                resource_totals["rds"] += 1
            elif resource["type"] == "eks":
                resource_totals["eks"] += 1
            elif resource["type"] == "lightsail":
                resource_totals["lightsail"] += 1
            elif resource["type"] == "nat":
                resource_totals["nat"] += resource["count"]
            elif resource["type"] == "elb":
                resource_totals["elb"] += resource["count"]

        # Count low-cost resources
        low_cost = user.get("low_cost_counts", {})
        resource_totals["volumes"] += low_cost.get("volumes", 0)
        resource_totals["snapshots"] += low_cost.get("snapshots", 0)
        resource_totals["ec2_stopped"] += low_cost.get("stopped_ec2", 0)
        resource_totals["eips"] += low_cost.get("eips", 0)

    # Build summary line
    summary_parts = []
    if resource_totals["ec2_running"] > 0:
        summary_parts.append(f"{resource_totals['ec2_running']} EC2 running")
    if resource_totals["ec2_stopped"] > 0:
        summary_parts.append(f"{resource_totals['ec2_stopped']} EC2 stopped")
    if resource_totals["rds"] > 0:
        summary_parts.append(f"{resource_totals['rds']} RDS")
    if resource_totals["eks"] > 0:
        summary_parts.append(f"{resource_totals['eks']} EKS")
    if resource_totals["volumes"] > 0:
        summary_parts.append(f"{resource_totals['volumes']} volumes")
    if resource_totals["snapshots"] > 0:
        summary_parts.append(f"{resource_totals['snapshots']} snapshots")
    if resource_totals["eips"] > 0:
        summary_parts.append(f"{resource_totals['eips']} EIPs")
    if resource_totals["nat"] > 0:
        summary_parts.append(f"{resource_totals['nat']} NAT")
    if resource_totals["elb"] > 0:
        summary_parts.append(f"{resource_totals['elb']} LBs")
    if resource_totals["lightsail"] > 0:
        summary_parts.append(f"{resource_totals['lightsail']} Lightsail")

    resource_summary = ", ".join(summary_parts) if summary_parts else "0 resources"

    # Build header
    user_word = "user" if total_users == 1 else "users"
    header_text = (
        f"🚨 *{account_name} Alert Report* • {_get_local_timestamp()}\n"
        f"📊 {total_users} {user_word}: {resource_summary}\n"
        "───────────────────────────────\n"
    )

    # Build per-user sections
    user_sections = []
    for user in sorted_data:
        section = f"\n👤 *{user['user_name']}* • `{user['account_id']}`\n"

        # Add high-cost resources with full details
        for resource in user["high_cost_resources"]:
            if resource["type"] == "ec2":
                section += f"• EC2: {resource['id']} ({resource['instance_type']}) {resource['state']} {resource['uptime_formatted']}"
                if resource.get("region"):
                    section += f" in {resource['region']}"
                section += "\n"
            elif resource["type"] == "rds":
                section += f"• RDS: {resource['name']} ({resource['instance_type']}) running {resource['uptime_formatted']}"
                if resource.get("region"):
                    section += f" in {resource['region']}"
                section += "\n"
            elif resource["type"] == "eks":
                section += f"• EKS: {resource['name']} (v{resource['version']}) running {resource['uptime_formatted']}"
                if resource.get("region"):
                    section += f" in {resource['region']}"
                section += "\n"
            elif resource["type"] == "lightsail":
                section += f"• Lightsail: {resource['name']} ({resource['bundle_id']}) {resource['state']} {resource['uptime_formatted']}"
                if resource.get("region"):
                    section += f" in {resource['region']}"
                section += "\n"
            elif resource["type"] == "nat":
                section += f"• NAT Gateways: {resource['count']} active"
                if resource.get("region"):
                    section += f" in {resource['region']}"
                section += "\n"
            elif resource["type"] == "elb":
                section += f"• Load Balancers: {resource['count']} active"
                if resource.get("region"):
                    section += f" in {resource['region']}"
                section += "\n"

        # Add low-cost resource counts
        low_cost = user.get("low_cost_counts", {})
        count_parts = []
        if low_cost.get("volumes", 0) > 0:
            count_parts.append(f"{low_cost['volumes']} volumes")
        if low_cost.get("snapshots", 0) > 0:
            count_parts.append(f"{low_cost['snapshots']} EBS snapshots")
        if low_cost.get("rds_snapshots", 0) > 0:
            count_parts.append(f"{low_cost['rds_snapshots']} RDS snapshots")
        if low_cost.get("stopped_ec2", 0) > 0:
            count_parts.append(f"{low_cost['stopped_ec2']} stopped EC2s")
        if low_cost.get("eips", 0) > 0:
            count_parts.append(f"{low_cost['eips']} EIPs")
        if low_cost.get("vpc_endpoints", 0) > 0:
            count_parts.append(f"{low_cost['vpc_endpoints']} VPC endpoints")

        if count_parts:
            section += f"• ({', '.join(count_parts)})\n"

        user_sections.append(section)

    # Combine all sections
    full_text = header_text + "".join(user_sections)

    return [{"type": "section", "text": {"type": "mrkdwn", "text": full_text}}]


def format_scan_summary(
    account_name: str, scanned: int, failed: int, total_resources: int
) -> List[Dict]:
    """Format scan summary message - matches bash script exactly.

    Args:
        account_name: Account name (e.g., dev)
        scanned: Number of accounts scanned
        failed: Number of accounts that failed
        total_resources: Total number of resources found

    Returns:
        Slack Block Kit blocks
    """
    # Compact system status message
    status_emoji = "✅" if failed == 0 else "⚠️"
    text = f"{status_emoji} System: Scanned {scanned} accounts, {failed} failed, {total_resources} total resources"
    return [{"type": "section", "text": {"type": "mrkdwn", "text": text}}]


def _validate_threshold(value, default_hours):
    """Validate and convert time threshold from hours to seconds.

    Args:
        value (str|None): Environment variable value in hours
        default_hours (int): Default value in hours

    Returns:
        int: Threshold in seconds
    """
    try:
        hours = int(value)
        if hours < 0:
            print(f"WARNING: Negative threshold {hours} hours, using default {default_hours} hours")
            return default_hours * 3600
        return hours * 3600
    except (ValueError, TypeError):
        if value is not None:
            print(f"WARNING: Invalid threshold '{value}', using default {default_hours} hours")
        return default_hours * 3600


def _validate_count_threshold(value, default_count):
    """Validate count or size threshold (no conversion).

    Args:
        value (str|None): Environment variable value
        default_count (int): Default value

    Returns:
        int: Threshold value
    """
    try:
        count = int(value)
        if count < 0:
            print(f"WARNING: Negative threshold {count}, using default {default_count}")
            return default_count
        return count
    except (ValueError, TypeError):
        if value is not None:
            print(f"WARNING: Invalid threshold '{value}', using default {default_count}")
        return default_count


def _get_thresholds():
    """Load all alert thresholds from environment variables.

    Returns:
        dict: Threshold values in seconds (for time) or units (for count)
    """
    return {
        # Time-based (hours → seconds)
        "ec2_running": _validate_threshold(os.environ.get("THRESHOLD_EC2_RUNNING_HOURS"), 12),
        "ec2_stopped": _validate_threshold(os.environ.get("THRESHOLD_EC2_STOPPED_HOURS"), 672),
        "rds": _validate_threshold(os.environ.get("THRESHOLD_RDS_HOURS"), 5),
        "eks": _validate_threshold(os.environ.get("THRESHOLD_EKS_HOURS"), 12),

        # Time-based (hours → seconds)
        "eip": _validate_threshold(os.environ.get("THRESHOLD_EIP_HOURS"), 2),
        "lightsail": _validate_threshold(os.environ.get("THRESHOLD_LIGHTSAIL_HOURS"), 168),
        "volume": _validate_threshold(os.environ.get("THRESHOLD_VOLUME_HOURS"), 672),
        "rds_snapshot": _validate_threshold(os.environ.get("THRESHOLD_RDS_SNAPSHOT_HOURS"), 2160),

        # Count-based (no conversion)
        "nat_gateway": _validate_count_threshold(os.environ.get("THRESHOLD_NAT_GATEWAY_COUNT"), 0),
        "elb": _validate_count_threshold(os.environ.get("THRESHOLD_ELB_COUNT"), 0),

        # Count-based (no conversion)
        "volume_count": _validate_count_threshold(
            os.environ.get("THRESHOLD_VOLUME_COUNT"), 5
        ),
        "eip_count": _validate_count_threshold(
            os.environ.get("THRESHOLD_EIP_COUNT"), 2
        ),
        "vpc_endpoint": _validate_count_threshold(
            os.environ.get("THRESHOLD_VPC_ENDPOINT_COUNT"), 2
        ),
        "lightsail_count": _validate_count_threshold(
            os.environ.get("THRESHOLD_LIGHTSAIL_COUNT"), 1
        ),
        "ebs_snapshot": _validate_count_threshold(
            os.environ.get("THRESHOLD_EBS_SNAPSHOT_COUNT"), 10
        ),
        "rds_snapshot_count": _validate_count_threshold(
            os.environ.get("THRESHOLD_RDS_SNAPSHOT_COUNT"), 5
        ),
    }


# Load thresholds once at module import time
THRESHOLDS = _get_thresholds()

# Monitoring alert display limits
MAX_RESOURCES_IN_MONITORING_ALERT = 10  # Limit resource list to avoid Slack message size issues


def should_alert(resource: Dict) -> bool:
    """Determine if resource exceeds threshold.

    Args:
        resource: Resource dictionary with type, state, uptime_seconds

    Returns:
        True if resource exceeds threshold
    """
    resource_type = resource["type"]
    state = resource.get("state", "running")
    uptime = resource["uptime_seconds"]

    if resource_type == "ec2" and state == "running":
        return uptime > THRESHOLDS["ec2_running"]
    elif resource_type == "ec2" and state == "stopped":
        return uptime > THRESHOLDS["ec2_stopped"]
    elif resource_type in ["rds", "eks", "eip", "lightsail", "volume", "rds_snapshot"]:
        return uptime > THRESHOLDS[resource_type]

    return False


def send_alerts(
    account_name: str,
    account_id: str,
    recipient_email: str,
    resources: List[Dict],
    slack_token: str,
    monitoring_channel: str,
    dry_run: bool = False,
    nat_count: int = 0,
    elb_count: int = 0,
    volume_count: int = 0,
    eip_count: int = 0,
    vpc_endpoint_count: int = 0,
    lightsail_count: int = 0,
    snapshot_count: int = 0,
    rds_snapshot_count: int = 0,
    rds_snapshot_size_gb: int = 0,
    test_user_email: Optional[str] = None,
) -> Dict:
    """Send Slack alerts for resources exceeding thresholds.

    Args:
        account_name: AWS account name
        account_id: AWS account ID
        recipient_email: User email address
        resources: List of resources that exceed thresholds
        slack_token: Slack bot token
        monitoring_channel: Monitoring channel ID (unused - monitoring handled by caller)
        dry_run: If True, skip DMs
        nat_count: Count of NAT Gateways (only shown if > 1)
        elb_count: Count of Load Balancers (only shown if > 1)
        volume_count: Count of unattached EBS volumes (only shown if > 5)
        eip_count: Count of unattached Elastic IPs (only shown if > 2)
        vpc_endpoint_count: Count of interface VPC endpoints (only shown if > 2)
        lightsail_count: Count of Lightsail instances (only shown if > 1)
        snapshot_count: Count of EBS snapshots (only shown if > 10)
        rds_snapshot_count: Count of RDS manual snapshots (only shown if > 10)
        rds_snapshot_size_gb: Total size in GB of RDS snapshots
        test_user_email: If set, redirect all DMs to this test user

    Returns:
        Monitoring data dict for consolidated report with keys:
            - user_name: str
            - account_id: str
            - high_cost_resources: List[Dict]
            - low_cost_counts: Dict[str, int]
    """
    # DRY_RUN: Skip DMs entirely
    if dry_run:
        print(f"[DRY_RUN] Skipping DM for {account_name}")
    else:
        # Determine recipient for DM
        recipient_email = recipient_email
        is_test_mode = test_user_email and test_user_email.strip()

        if is_test_mode:
            recipient_email = test_user_email
            print(
                f"[TEST_MODE] Sending DM for {account_name} to {test_user_email}"
            )

        # Send DM (or test user DM)
        user_id = find_slack_user(recipient_email, slack_token)
        if user_id:
            channel = open_dm_channel(user_id, slack_token)
            if channel:
                dm_blocks = format_account_dm(
                    account_name, resources, nat_count, elb_count, volume_count,
                    eip_count, vpc_endpoint_count, lightsail_count, snapshot_count,
                    rds_snapshot_count, rds_snapshot_size_gb
                )

                # Add test mode header if redirecting
                if is_test_mode:
                    test_header = {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"⚠️ *TEST MODE: Alert for {account_name} ({account_id})*"
                        }
                    }
                    dm_blocks.insert(0, test_header)

                success = send_message(channel, dm_blocks, slack_token)
                if not success:
                    print(f"Warning: Failed to send DM to {recipient_email}")
            else:
                print(f"Warning: Could not open DM channel for {recipient_email}")
        else:
            error_msg = f"Warning: Slack user not found for {recipient_email}"
            if is_test_mode:
                error_msg += " (test user)"
            print(error_msg)

    # Build monitoring data for consolidated report
    # Classify resources into high-cost (show details) and low-cost (count only)
    high_cost_resources = []
    low_cost_counts = {
        "volumes": 0,
        "snapshots": 0,
        "rds_snapshots": 0,
        "stopped_ec2": 0,
        "eips": 0,
        "vpc_endpoints": 0,
    }

    # Process individual resources that exceeded time thresholds
    for resource in resources:
        resource_type = resource["type"]

        # High-cost resources: show full details in monitoring channel
        if resource_type == "ec2" and resource["state"].lower() == "running":
            high_cost_resources.append(resource)
        elif resource_type in ["rds", "eks", "lightsail"]:
            high_cost_resources.append(resource)
        # Low-cost resources: count only (stopped EC2, volumes with age threshold)
        elif resource_type == "ec2" and resource["state"].lower() == "stopped":
            low_cost_counts["stopped_ec2"] += 1
        elif resource_type == "volume":
            low_cost_counts["volumes"] += 1
        elif resource_type == "eip":
            low_cost_counts["eips"] += 1
        elif resource_type == "rds_snapshot":
            low_cost_counts["rds_snapshots"] += 1

    # Add NAT and ELB as high-cost count-based resources
    if nat_count > 0:
        high_cost_resources.append({"type": "nat", "count": nat_count})
    if elb_count > 0:
        high_cost_resources.append({"type": "elb", "count": elb_count})

    # Override with count parameters (these represent count threshold violations)
    # Use max() to handle both time threshold (from resources) and count threshold
    if volume_count > 0:
        low_cost_counts["volumes"] = max(low_cost_counts["volumes"], volume_count)
    if eip_count > 0:
        low_cost_counts["eips"] = max(low_cost_counts["eips"], eip_count)
    if vpc_endpoint_count > 0:
        low_cost_counts["vpc_endpoints"] = vpc_endpoint_count
    if snapshot_count > 0:
        low_cost_counts["snapshots"] = snapshot_count
    if rds_snapshot_count > 0:
        low_cost_counts["rds_snapshots"] = max(low_cost_counts["rds_snapshots"], rds_snapshot_count)

    return {
        "user_name": account_name,
        "account_id": account_id,
        "high_cost_resources": high_cost_resources,
        "low_cost_counts": low_cost_counts,
    }
