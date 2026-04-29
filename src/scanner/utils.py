"""Utility functions for resource scanning."""

import os
import boto3
from datetime import datetime
from typing import Tuple, Dict


DEFAULT_ASSUME_ROLE_NAME = "OrganizationAccountAccessRole"


def calculate_uptime(launch_time: datetime) -> Tuple[int, str]:
    """Calculate resource uptime from launch timestamp.

    Args:
        launch_time: Resource creation/launch timestamp (UTC)

    Returns:
        Tuple of (total_seconds, human_readable_format)
        Example: (49440, "13h 44m")

    Raises:
        ValueError: If launch_time is in the future
    """
    now = datetime.now(launch_time.tzinfo)
    delta = now - launch_time

    total_seconds = int(delta.total_seconds())

    if total_seconds < 0:
        raise ValueError("Launch time cannot be in the future")

    formatted = _format_duration_compact(total_seconds)
    return total_seconds, formatted


def _format_duration_compact(seconds: int) -> str:
    """Format duration as 'Xd Yh' without minutes/seconds.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "11d 6h", "12h", or "7d"

    Examples:
        - 43200 (12h) → "12h"
        - 129600 (36h) → "1d 12h"
        - 648000 (7.5d) → "7d 12h"
        - 972000 (270h) → "11d 6h"
    """
    hours = seconds // 3600
    if hours < 24:
        return f"{hours}h"

    days = hours // 24
    remaining_hours = hours % 24

    if remaining_hours == 0:
        return f"{days}d"
    return f"{days}d {remaining_hours}h"


def assume_role(account_id: str) -> Dict[str, str]:
    """Assume role in target account.

    Uses ASSUME_ROLE_NAME env var if set, otherwise defaults to
    OrganizationAccountAccessRole.

    Args:
        account_id: AWS account ID to assume role in

    Returns:
        Dictionary of AWS credentials for boto3 client creation
        Keys: aws_access_key_id, aws_secret_access_key, aws_session_token

    Raises:
        Exception: If AssumeRole fails
    """
    role_name = os.environ.get("ASSUME_ROLE_NAME", DEFAULT_ASSUME_ROLE_NAME)
    sts = boto3.client("sts")
    response = sts.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/{role_name}",
        RoleSessionName="aws-org-scanner",
    )

    credentials = response["Credentials"]
    return {
        "aws_access_key_id": credentials["AccessKeyId"],
        "aws_secret_access_key": credentials["SecretAccessKey"],
        "aws_session_token": credentials["SessionToken"],
    }
