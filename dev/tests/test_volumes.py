"""Unit tests for EBS volume scanning."""

import pytest
from moto import mock_ec2
import boto3
from datetime import datetime, timezone
from scanner.volumes import scan_volumes


@mock_ec2
def test_scan_volumes_finds_available_volumes():
    """Test scanning finds unattached (available) volumes."""
    # Setup: Create EC2 client and volumes
    ec2 = boto3.client("ec2", region_name="ap-south-1")

    # Create 5 available volumes
    volume_ids = []
    for i in range(5):
        response = ec2.create_volume(
            AvailabilityZone="ap-south-1a",
            Size=10 + i,
        )
        volume_ids.append(response["VolumeId"])

    # Get credentials (moto doesn't need real creds)
    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan volumes
    volumes = scan_volumes(credentials, "ap-south-1")

    # Verify: Should find 5 volumes
    assert len(volumes) == 5

    # Verify: Each volume has correct structure
    for i, volume in enumerate(volumes):
        assert "id" in volume
        assert "size_gb" in volume
        assert "region" in volume
        assert volume["region"] == "ap-south-1"
        assert volume["size_gb"] == 10 + i


@mock_ec2
def test_scan_volumes_ignores_in_use_volumes():
    """Test scanning only finds available volumes, not in-use ones."""
    # Setup: Create EC2 instance and attach volume
    ec2 = boto3.client("ec2", region_name="ap-south-1")

    # Create instance
    run_response = ec2.run_instances(
        ImageId="ami-12345678",
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
    )
    instance_id = run_response["Instances"][0]["InstanceId"]

    # Create volume and attach to instance
    volume_response = ec2.create_volume(
        AvailabilityZone="ap-south-1a",
        Size=20,
    )
    volume_id = volume_response["VolumeId"]

    ec2.attach_volume(
        Device="/dev/sdf",
        InstanceId=instance_id,
        VolumeId=volume_id,
    )

    # Get credentials
    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan volumes
    volumes = scan_volumes(credentials, "ap-south-1")

    # Verify: Should find 0 volumes (attached volume is "in-use", not "available")
    # Note: moto may not perfectly simulate volume state transitions
    # In real AWS, attached volumes are "in-use" state
    assert len(volumes) == 0 or all(v["id"] != volume_id for v in volumes)


@mock_ec2
def test_scan_volumes_empty_region():
    """Test scanning region with no volumes."""
    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan region with no volumes
    volumes = scan_volumes(credentials, "ap-south-1")

    # Verify: Should return empty list
    assert volumes == []


@mock_ec2
def test_scan_volumes_multiple_sizes():
    """Test scanning volumes with different sizes."""
    ec2 = boto3.client("ec2", region_name="ap-south-1")

    # Create volumes with different sizes
    sizes = [8, 50, 100, 500, 1000]
    for size in sizes:
        ec2.create_volume(
            AvailabilityZone="ap-south-1a",
            Size=size,
        )

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan volumes
    volumes = scan_volumes(credentials, "ap-south-1")

    # Verify: Should find all volumes with correct sizes
    assert len(volumes) == 5
    found_sizes = sorted([v["size_gb"] for v in volumes])
    assert found_sizes == sorted(sizes)


@mock_ec2
def test_scan_volumes_includes_created_at():
    """Test that scanner extracts CreateTime field."""
    ec2 = boto3.client("ec2", region_name="ap-south-1")

    # Create volume
    ec2.create_volume(AvailabilityZone="ap-south-1a", Size=20)

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan volumes
    result = scan_volumes(credentials, "ap-south-1")

    # Verify: Should include created_at field
    assert len(result) == 1
    assert "created_at" in result[0]
    assert isinstance(result[0]["created_at"], datetime)


@mock_ec2
def test_scan_volumes_backward_compatibility():
    """CRITICAL: Verify count threshold still works."""
    ec2 = boto3.client("ec2", region_name="ap-south-1")

    # Create 6 volumes (all recent)
    for i in range(6):
        ec2.create_volume(AvailabilityZone="ap-south-1a", Size=10)

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan volumes
    result = scan_volumes(credentials, "ap-south-1")

    # Verify: Backward compatibility - count threshold should work
    assert len(result) == 6
    # Verify all volumes have required fields including new created_at
    for vol in result:
        assert "id" in vol
        assert "size_gb" in vol
        assert "region" in vol
        assert "created_at" in vol
