"""Unit tests for VPC endpoint scanning."""

import pytest
from moto import mock_ec2
import boto3
from scanner.vpc_endpoints import scan_vpc_endpoints


@mock_ec2
def test_scan_vpc_endpoints_counts_interface_only():
    """Test scanning counts only interface endpoints, not gateway."""
    ec2 = boto3.client("ec2", region_name="ap-south-1")

    # Create VPC
    vpc_response = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc_response["Vpc"]["VpcId"]

    # Create 3 interface endpoints
    for i in range(3):
        ec2.create_vpc_endpoint(
            VpcId=vpc_id,
            VpcEndpointType="Interface",
            ServiceName=f"com.amazonaws.ap-south-1.service{i}",
        )

    # Create 2 gateway endpoints (should not be counted)
    ec2.create_vpc_endpoint(
        VpcId=vpc_id,
        VpcEndpointType="Gateway",
        ServiceName="com.amazonaws.ap-south-1.s3",
        RouteTableIds=[],
    )

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan VPC endpoints
    result = scan_vpc_endpoints(credentials, "ap-south-1")

    # Verify: Should count only 3 interface endpoints
    assert result["count"] == 3
    assert result["region"] == "ap-south-1"
    assert len(result["service_names"]) == 3


@mock_ec2
def test_scan_vpc_endpoints_empty_region():
    """Test scanning region with no VPC endpoints."""
    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan region with no endpoints
    result = scan_vpc_endpoints(credentials, "ap-south-1")

    # Verify: Should return count of 0
    assert result["count"] == 0
    assert result["service_names"] == []
    assert result["region"] == "ap-south-1"


@mock_ec2
def test_scan_vpc_endpoints_gateway_only():
    """Test scanning region with only gateway endpoints (free)."""
    ec2 = boto3.client("ec2", region_name="ap-south-1")

    # Create VPC
    vpc_response = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc_response["Vpc"]["VpcId"]

    # Create 2 gateway endpoints (S3 and DynamoDB - both free)
    ec2.create_vpc_endpoint(
        VpcId=vpc_id,
        VpcEndpointType="Gateway",
        ServiceName="com.amazonaws.ap-south-1.s3",
        RouteTableIds=[],
    )

    ec2.create_vpc_endpoint(
        VpcId=vpc_id,
        VpcEndpointType="Gateway",
        ServiceName="com.amazonaws.ap-south-1.dynamodb",
        RouteTableIds=[],
    )

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan VPC endpoints
    result = scan_vpc_endpoints(credentials, "ap-south-1")

    # Verify: Gateway endpoints are free, should not be counted
    assert result["count"] == 0


@mock_ec2
def test_scan_vpc_endpoints_multiple_interface():
    """Test scanning with multiple interface endpoints."""
    ec2 = boto3.client("ec2", region_name="ap-south-1")

    # Create VPC
    vpc_response = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc_response["Vpc"]["VpcId"]

    # Create 5 interface endpoints (common AWS services)
    services = ["ec2", "rds", "secretsmanager", "cloudwatch", "lambda"]
    for service in services:
        ec2.create_vpc_endpoint(
            VpcId=vpc_id,
            VpcEndpointType="Interface",
            ServiceName=f"com.amazonaws.ap-south-1.{service}",
        )

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan VPC endpoints
    result = scan_vpc_endpoints(credentials, "ap-south-1")

    # Verify: Should count all 5 interface endpoints
    assert result["count"] == 5
    assert len(result["service_names"]) == 5

    # Verify service names are extracted correctly
    for service in services:
        assert service in result["service_names"]


@mock_ec2
def test_scan_vpc_endpoints_mixed_types():
    """Test scanning with mix of interface and gateway endpoints."""
    ec2 = boto3.client("ec2", region_name="ap-south-1")

    # Create VPC
    vpc_response = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc_response["Vpc"]["VpcId"]

    # Create 4 interface endpoints
    for i in range(4):
        ec2.create_vpc_endpoint(
            VpcId=vpc_id,
            VpcEndpointType="Interface",
            ServiceName=f"com.amazonaws.ap-south-1.service{i}",
        )

    # Create 3 gateway endpoints
    for i in range(3):
        ec2.create_vpc_endpoint(
            VpcId=vpc_id,
            VpcEndpointType="Gateway",
            ServiceName=f"com.amazonaws.ap-south-1.gateway{i}",
            RouteTableIds=[],
        )

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan VPC endpoints
    result = scan_vpc_endpoints(credentials, "ap-south-1")

    # Verify: Should count only 4 interface endpoints
    assert result["count"] == 4
    assert len(result["service_names"]) == 4


@mock_ec2
def test_scan_vpc_endpoints_service_name_extraction():
    """Test service name extraction from endpoint ServiceName."""
    ec2 = boto3.client("ec2", region_name="ap-south-1")

    # Create VPC
    vpc_response = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc_response["Vpc"]["VpcId"]

    # Create interface endpoint with full service name
    ec2.create_vpc_endpoint(
        VpcId=vpc_id,
        VpcEndpointType="Interface",
        ServiceName="com.amazonaws.ap-south-1.secretsmanager",
    )

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }

    # Execute: Scan VPC endpoints
    result = scan_vpc_endpoints(credentials, "ap-south-1")

    # Verify: Service name extracted correctly
    assert result["count"] == 1
    assert "secretsmanager" in result["service_names"]
