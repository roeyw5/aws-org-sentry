"""Tests for EC2 scanning."""

import boto3
from moto import mock_ec2
from scanner.ec2 import scan_ec2_instances


@mock_ec2
def test_scan_ec2_instances_running():
    """Test EC2 scanning finds running instances."""
    ec2 = boto3.client("ec2", region_name="us-east-1")

    # Launch instance
    response = ec2.run_instances(
        ImageId="ami-12345", InstanceType="t2.micro", MinCount=1, MaxCount=1
    )
    instance_id = response["Instances"][0]["InstanceId"]

    # Scan with empty credentials (moto doesn't validate)
    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }
    instances = scan_ec2_instances(credentials, "us-east-1")

    assert len(instances) == 1
    assert instances[0]["id"] == instance_id
    assert instances[0]["name"] == "No Name"
    assert instances[0]["type"] == "t2.micro"
    assert instances[0]["state"] == "running"
    assert "launch_time" in instances[0]


@mock_ec2
def test_scan_ec2_instances_excludes_terminated():
    """Test that terminated instances are excluded."""
    ec2 = boto3.client("ec2", region_name="us-east-1")

    # Launch and terminate instance
    response = ec2.run_instances(
        ImageId="ami-12345", InstanceType="t2.micro", MinCount=1, MaxCount=1
    )
    instance_id = response["Instances"][0]["InstanceId"]
    ec2.terminate_instances(InstanceIds=[instance_id])

    # Scan
    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }
    instances = scan_ec2_instances(credentials, "us-east-1")

    # Terminated instances should not appear
    terminated_ids = [inst["id"] for inst in instances if inst["state"] == "terminated"]
    assert instance_id not in terminated_ids


@mock_ec2
def test_scan_ec2_instances_stopped():
    """Test that stopped instances are included."""
    ec2 = boto3.client("ec2", region_name="us-east-1")

    # Launch and stop instance
    response = ec2.run_instances(
        ImageId="ami-12345", InstanceType="t3.small", MinCount=1, MaxCount=1
    )
    instance_id = response["Instances"][0]["InstanceId"]
    ec2.stop_instances(InstanceIds=[instance_id])

    # Scan
    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }
    instances = scan_ec2_instances(credentials, "us-east-1")

    # Should find stopped instance
    stopped_instances = [inst for inst in instances if inst["id"] == instance_id]
    assert len(stopped_instances) == 1
    assert stopped_instances[0]["state"] == "stopped"


@mock_ec2
def test_scan_ec2_instances_empty_region():
    """Test scanning region with no instances."""
    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }
    instances = scan_ec2_instances(credentials, "us-west-2")

    assert instances == []


@mock_ec2
def test_scan_ec2_instances_with_name_tag():
    """Test EC2 scanning extracts Name tag."""
    ec2 = boto3.client("ec2", region_name="us-east-1")

    # Launch instance with Name tag
    response = ec2.run_instances(
        ImageId="ami-12345",
        InstanceType="t3.medium",
        MinCount=1,
        MaxCount=1,
        TagSpecifications=[
            {"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "jenkins"}]}
        ],
    )
    instance_id = response["Instances"][0]["InstanceId"]

    # Scan
    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }
    instances = scan_ec2_instances(credentials, "us-east-1")

    assert len(instances) == 1
    assert instances[0]["id"] == instance_id
    assert instances[0]["name"] == "jenkins"
    assert instances[0]["type"] == "t3.medium"


@mock_ec2
def test_scan_ec2_instances_without_name_tag():
    """Test EC2 scanning defaults to 'No Name' when Name tag missing."""
    ec2 = boto3.client("ec2", region_name="us-east-1")

    # Launch instance without Name tag
    response = ec2.run_instances(
        ImageId="ami-12345", InstanceType="t2.micro", MinCount=1, MaxCount=1
    )
    instance_id = response["Instances"][0]["InstanceId"]

    # Scan
    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }
    instances = scan_ec2_instances(credentials, "us-east-1")

    assert len(instances) == 1
    assert instances[0]["id"] == instance_id
    assert instances[0]["name"] == "No Name"
