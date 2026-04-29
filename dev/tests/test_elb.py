"""Unit tests for Load Balancer scanner module."""

import pytest
from moto import mock_elbv2, mock_elb, mock_ec2
import boto3

from scanner.elb import scan_load_balancers


@mock_ec2
@mock_elbv2
@mock_elb
def test_scan_load_balancers_no_resources():
    """Test scanning when no load balancers exist."""
    credentials = {
        'aws_access_key_id': 'testing',
        'aws_secret_access_key': 'testing',
        'aws_session_token': 'testing'
    }

    count = scan_load_balancers(credentials, 'us-east-1')
    assert count == 0


@mock_ec2
@mock_elbv2
def test_scan_load_balancers_alb_only():
    """Test scanning with Application Load Balancer only."""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    elbv2 = boto3.client('elbv2', region_name='us-east-1')

    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']

    subnet1 = ec2.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24', AvailabilityZone='us-east-1a')
    subnet2 = ec2.create_subnet(VpcId=vpc_id, CidrBlock='10.0.2.0/24', AvailabilityZone='us-east-1b')

    elbv2.create_load_balancer(
        Name='test-alb',
        Subnets=[subnet1['Subnet']['SubnetId'], subnet2['Subnet']['SubnetId']],
        Scheme='internet-facing',
        Type='application'
    )

    credentials = {
        'aws_access_key_id': 'testing',
        'aws_secret_access_key': 'testing',
        'aws_session_token': 'testing'
    }

    count = scan_load_balancers(credentials, 'us-east-1')
    assert count == 1


@mock_ec2
@mock_elbv2
def test_scan_load_balancers_nlb_only():
    """Test scanning with Network Load Balancer only."""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    elbv2 = boto3.client('elbv2', region_name='us-east-1')

    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']

    subnet1 = ec2.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24', AvailabilityZone='us-east-1a')
    subnet2 = ec2.create_subnet(VpcId=vpc_id, CidrBlock='10.0.2.0/24', AvailabilityZone='us-east-1b')

    elbv2.create_load_balancer(
        Name='test-nlb',
        Subnets=[subnet1['Subnet']['SubnetId'], subnet2['Subnet']['SubnetId']],
        Scheme='internet-facing',
        Type='network'
    )

    credentials = {
        'aws_access_key_id': 'testing',
        'aws_secret_access_key': 'testing',
        'aws_session_token': 'testing'
    }

    count = scan_load_balancers(credentials, 'us-east-1')
    assert count == 1


@mock_ec2
@mock_elbv2
@mock_elb
def test_scan_load_balancers_clb_only():
    """Test scanning with Classic Load Balancer only."""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    elb = boto3.client('elb', region_name='us-east-1')

    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']

    subnet1 = ec2.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24', AvailabilityZone='us-east-1a')

    elb.create_load_balancer(
        LoadBalancerName='test-clb',
        Listeners=[{
            'Protocol': 'HTTP',
            'LoadBalancerPort': 80,
            'InstancePort': 80
        }],
        AvailabilityZones=['us-east-1a']
    )

    credentials = {
        'aws_access_key_id': 'testing',
        'aws_secret_access_key': 'testing',
        'aws_session_token': 'testing'
    }

    count = scan_load_balancers(credentials, 'us-east-1')
    assert count == 1


@mock_ec2
@mock_elbv2
@mock_elb
def test_scan_load_balancers_mixed_types():
    """Test scanning with multiple load balancer types."""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    elbv2 = boto3.client('elbv2', region_name='us-east-1')
    elb = boto3.client('elb', region_name='us-east-1')

    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']

    subnet1 = ec2.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24', AvailabilityZone='us-east-1a')
    subnet2 = ec2.create_subnet(VpcId=vpc_id, CidrBlock='10.0.2.0/24', AvailabilityZone='us-east-1b')

    # Create ALB
    elbv2.create_load_balancer(
        Name='test-alb-1',
        Subnets=[subnet1['Subnet']['SubnetId'], subnet2['Subnet']['SubnetId']],
        Type='application'
    )

    # Create another ALB
    elbv2.create_load_balancer(
        Name='test-alb-2',
        Subnets=[subnet1['Subnet']['SubnetId'], subnet2['Subnet']['SubnetId']],
        Type='application'
    )

    # Create NLB
    elbv2.create_load_balancer(
        Name='test-nlb',
        Subnets=[subnet1['Subnet']['SubnetId'], subnet2['Subnet']['SubnetId']],
        Type='network'
    )

    # Create CLB
    elb.create_load_balancer(
        LoadBalancerName='test-clb',
        Listeners=[{
            'Protocol': 'HTTP',
            'LoadBalancerPort': 80,
            'InstancePort': 80
        }],
        AvailabilityZones=['us-east-1a']
    )

    credentials = {
        'aws_access_key_id': 'testing',
        'aws_secret_access_key': 'testing',
        'aws_session_token': 'testing'
    }

    count = scan_load_balancers(credentials, 'us-east-1')
    assert count == 4


@mock_elbv2
@mock_elb
def test_scan_load_balancers_handles_exceptions():
    """Test error handling for API failures."""
    credentials = {
        'aws_access_key_id': 'invalid',
        'aws_secret_access_key': 'invalid',
        'aws_session_token': 'invalid'
    }

    count = scan_load_balancers(credentials, 'invalid-region')
    assert count == 0
