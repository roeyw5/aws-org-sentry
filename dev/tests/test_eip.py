"""Unit tests for Elastic IP scanning."""

import pytest
from moto import mock_ec2
import boto3
from scanner.eip import scan_elastic_ips


@mock_ec2
def test_scan_elastic_ips_finds_unattached():
    """Test scanning finds unattached Elastic IPs."""
    ec2 = boto3.client("ec2", region_name="ap-south-1")

    # Allocate 3 unattached EIPs
    eip1 = ec2.allocate_address(Domain="vpc")
    eip2 = ec2.allocate_address(Domain="vpc")
    eip3 = ec2.allocate_address(Domain="vpc")

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan EIPs
    eips = scan_elastic_ips(credentials, "ap-south-1")

    # Verify: Should find 3 unattached EIPs
    assert len(eips) == 3

    # Verify: Each EIP has correct structure
    for eip in eips:
        assert "id" in eip
        assert "public_ip" in eip
        assert "allocation_time" in eip
        assert "region" in eip
        assert eip["region"] == "ap-south-1"


@mock_ec2
def test_scan_elastic_ips_ignores_attached():
    """Test scanning only finds unattached EIPs, not attached ones."""
    ec2 = boto3.client("ec2", region_name="ap-south-1")

    # Create instance
    run_response = ec2.run_instances(
        ImageId="ami-12345678",
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
    )
    instance_id = run_response["Instances"][0]["InstanceId"]

    # Allocate EIP and associate with instance
    eip_response = ec2.allocate_address(Domain="vpc")
    allocation_id = eip_response["AllocationId"]

    ec2.associate_address(InstanceId=instance_id, AllocationId=allocation_id)

    # Allocate one unattached EIP
    ec2.allocate_address(Domain="vpc")

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan EIPs
    eips = scan_elastic_ips(credentials, "ap-south-1")

    # Verify: Should find only 1 unattached EIP (not the attached one)
    assert len(eips) == 1
    assert eips[0]["id"] != allocation_id


@mock_ec2
def test_scan_elastic_ips_empty_region():
    """Test scanning region with no EIPs."""
    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan region with no EIPs
    eips = scan_elastic_ips(credentials, "ap-south-1")

    # Verify: Should return empty list
    assert eips == []


@mock_ec2
def test_scan_elastic_ips_multiple_unattached():
    """Test scanning with multiple unattached EIPs."""
    ec2 = boto3.client("ec2", region_name="ap-south-1")

    # Allocate 5 unattached EIPs
    allocation_ids = []
    for _ in range(5):
        response = ec2.allocate_address(Domain="vpc")
        allocation_ids.append(response["AllocationId"])

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan EIPs
    eips = scan_elastic_ips(credentials, "ap-south-1")

    # Verify: Should find all 5 unattached EIPs
    assert len(eips) == 5
    found_ids = [eip["id"] for eip in eips]
    for alloc_id in allocation_ids:
        assert alloc_id in found_ids


@mock_ec2
def test_scan_elastic_ips_mixed_attached_unattached():
    """Test scanning with mix of attached and unattached EIPs."""
    ec2 = boto3.client("ec2", region_name="ap-south-1")

    # Create 2 instances
    run_response = ec2.run_instances(
        ImageId="ami-12345678", MinCount=2, MaxCount=2, InstanceType="t2.micro"
    )
    instance_ids = [i["InstanceId"] for i in run_response["Instances"]]

    # Allocate and attach 2 EIPs
    for instance_id in instance_ids:
        eip = ec2.allocate_address(Domain="vpc")
        ec2.associate_address(InstanceId=instance_id, AllocationId=eip["AllocationId"])

    # Allocate 3 unattached EIPs
    for _ in range(3):
        ec2.allocate_address(Domain="vpc")

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan EIPs
    eips = scan_elastic_ips(credentials, "ap-south-1")

    # Verify: Should find only 3 unattached EIPs (not the 2 attached)
    assert len(eips) == 3
