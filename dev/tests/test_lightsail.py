"""Unit tests for Lightsail instance scanning."""

from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from scanner.lightsail import scan_lightsail_instances


@patch("boto3.client")
def test_scan_lightsail_instances_running(mock_boto_client):
    """Test scanning returns running Lightsail instances."""
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client

    mock_client.get_instances.return_value = {
        "instances": [
            {
                "name": "test-instance",
                "bundleId": "nano_2_0",
                "state": {"name": "running"},
                "createdAt": datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
                "location": {"regionName": "ap-south-1"},
            }
        ]
    }

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan Lightsail instances
    result = scan_lightsail_instances(credentials, "ap-south-1")

    # Verify: Should find 1 running instance
    assert len(result) == 1
    assert result[0]["name"] == "test-instance"
    assert result[0]["bundle_id"] == "nano_2_0"
    assert result[0]["state"] == "running"
    assert result[0]["region"] == "ap-south-1"
    assert "created_at" in result[0]


@patch("boto3.client")
def test_scan_lightsail_instances_stopped(mock_boto_client):
    """Test scanning includes stopped Lightsail instances (they still incur charges)."""
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client

    mock_client.get_instances.return_value = {
        "instances": [
            {
                "name": "stopped-instance",
                "bundleId": "micro_2_0",
                "state": {"name": "stopped"},
                "createdAt": datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
                "location": {"regionName": "ap-south-1"},
            }
        ]
    }

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan Lightsail instances
    result = scan_lightsail_instances(credentials, "ap-south-1")

    # Verify: Should find stopped instance (still incurs charges)
    assert len(result) == 1
    assert result[0]["state"] == "stopped"


@patch("boto3.client")
def test_scan_lightsail_instances_filtering_terminated(mock_boto_client):
    """Test scanning filters out terminated/terminating instances."""
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client

    mock_client.get_instances.return_value = {
        "instances": [
            {
                "name": "running-instance",
                "bundleId": "nano_2_0",
                "state": {"name": "running"},
                "createdAt": datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
                "location": {"regionName": "ap-south-1"},
            },
            {
                "name": "terminated-instance",
                "bundleId": "nano_2_0",
                "state": {"name": "terminated"},
                "createdAt": datetime(2025, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
                "location": {"regionName": "ap-south-1"},
            },
            {
                "name": "terminating-instance",
                "bundleId": "nano_2_0",
                "state": {"name": "terminating"},
                "createdAt": datetime(2025, 9, 15, 12, 0, 0, tzinfo=timezone.utc),
                "location": {"regionName": "ap-south-1"},
            },
        ]
    }

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan Lightsail instances
    result = scan_lightsail_instances(credentials, "ap-south-1")

    # Verify: Should find only running instance, exclude terminated/terminating
    assert len(result) == 1
    assert result[0]["name"] == "running-instance"
    assert result[0]["state"] == "running"


@patch("boto3.client")
def test_scan_lightsail_instances_empty(mock_boto_client):
    """Test scanning region with no Lightsail instances."""
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client

    mock_client.get_instances.return_value = {"instances": []}

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan region with no instances
    result = scan_lightsail_instances(credentials, "ap-south-1")

    # Verify: Should return empty list
    assert result == []


@patch("boto3.client")
def test_scan_lightsail_instances_multiple_states(mock_boto_client):
    """Test scanning with mix of running, stopped, and pending instances."""
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client

    mock_client.get_instances.return_value = {
        "instances": [
            {
                "name": "running-1",
                "bundleId": "nano_2_0",
                "state": {"name": "running"},
                "createdAt": datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
                "location": {"regionName": "ap-south-1"},
            },
            {
                "name": "stopped-1",
                "bundleId": "micro_2_0",
                "state": {"name": "stopped"},
                "createdAt": datetime(2025, 10, 5, 12, 0, 0, tzinfo=timezone.utc),
                "location": {"regionName": "ap-south-1"},
            },
            {
                "name": "pending-1",
                "bundleId": "small_2_0",
                "state": {"name": "pending"},
                "createdAt": datetime(2025, 10, 10, 12, 0, 0, tzinfo=timezone.utc),
                "location": {"regionName": "ap-south-1"},
            },
        ]
    }

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan Lightsail instances
    result = scan_lightsail_instances(credentials, "ap-south-1")

    # Verify: Should find all 3 non-terminated instances
    assert len(result) == 3
    states = [r["state"] for r in result]
    assert "running" in states
    assert "stopped" in states
    assert "pending" in states


@patch("boto3.client")
def test_scan_lightsail_instances_permission_denied(mock_boto_client):
    """Test graceful handling of permission errors."""
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client

    mock_client.get_instances.side_effect = Exception("AccessDenied")

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan with permission error
    result = scan_lightsail_instances(credentials, "ap-south-1")

    # Verify: Should return empty list and not crash
    assert result == []


@patch("boto3.client")
def test_scan_lightsail_instances_multiple_bundles(mock_boto_client):
    """Test scanning detects various bundle sizes."""
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client

    mock_client.get_instances.return_value = {
        "instances": [
            {
                "name": "nano-instance",
                "bundleId": "nano_2_0",
                "state": {"name": "running"},
                "createdAt": datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
                "location": {"regionName": "ap-south-1"},
            },
            {
                "name": "medium-instance",
                "bundleId": "medium_2_0",
                "state": {"name": "running"},
                "createdAt": datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
                "location": {"regionName": "ap-south-1"},
            },
            {
                "name": "xlarge-instance",
                "bundleId": "xlarge_2_0",
                "state": {"name": "stopped"},
                "createdAt": datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
                "location": {"regionName": "ap-south-1"},
            },
        ]
    }

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan Lightsail instances
    result = scan_lightsail_instances(credentials, "ap-south-1")

    # Verify: Should find all 3 instances with different bundles
    assert len(result) == 3
    bundles = [r["bundle_id"] for r in result]
    assert "nano_2_0" in bundles
    assert "medium_2_0" in bundles
    assert "xlarge_2_0" in bundles
