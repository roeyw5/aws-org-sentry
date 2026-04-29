"""Tests for EKS scanning."""

import boto3
from moto import mock_eks, mock_ec2
from scanner.eks import scan_eks_clusters


@mock_eks
@mock_ec2
def test_scan_eks_clusters():
    """Test EKS scanning finds clusters."""
    # EKS requires VPC resources
    ec2 = boto3.client("ec2", region_name="us-east-1")
    eks = boto3.client("eks", region_name="us-east-1")

    # Create VPC and subnets (required for EKS)
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]

    subnet1 = ec2.create_subnet(VpcId=vpc_id, CidrBlock="10.0.1.0/24")
    subnet2 = ec2.create_subnet(VpcId=vpc_id, CidrBlock="10.0.2.0/24")

    # Create EKS cluster
    eks.create_cluster(
        name="test-cluster",
        version="1.27",
        roleArn="arn:aws:iam::123456789012:role/eks-service-role",
        resourcesVpcConfig={
            "subnetIds": [subnet1["Subnet"]["SubnetId"], subnet2["Subnet"]["SubnetId"]]
        },
    )

    # Scan
    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }
    clusters = scan_eks_clusters(credentials, "us-east-1")

    assert len(clusters) == 1
    assert clusters[0]["name"] == "test-cluster"
    assert clusters[0]["version"] == "1.27"
    assert clusters[0]["status"] == "ACTIVE"
    assert "created_at" in clusters[0]


@mock_eks
def test_scan_eks_clusters_empty():
    """Test EKS scanning with no clusters."""
    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }
    clusters = scan_eks_clusters(credentials, "us-west-2")

    assert clusters == []
