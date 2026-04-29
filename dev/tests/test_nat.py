"""Unit tests for NAT Gateway scanner module."""

import pytest
from moto import mock_ec2
import boto3

from scanner.nat import scan_nat_gateways


@mock_ec2
def test_scan_nat_gateways_no_resources():
    """Test scanning when no NAT Gateways exist."""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    vpc_response = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc_response['Vpc']['VpcId']

    subnet_response = ec2.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')
    subnet_id = subnet_response['Subnet']['SubnetId']

    credentials = {
        'aws_access_key_id': 'testing',
        'aws_secret_access_key': 'testing',
        'aws_session_token': 'testing'
    }

    count = scan_nat_gateways(credentials, 'us-east-1')
    assert count == 0


@mock_ec2
def test_scan_nat_gateways_single_available():
    """Test scanning with one available NAT Gateway."""
    ec2 = boto3.client('ec2', region_name='us-east-1')

    vpc_response = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc_response['Vpc']['VpcId']

    subnet_response = ec2.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')
    subnet_id = subnet_response['Subnet']['SubnetId']

    allocation_response = ec2.allocate_address(Domain='vpc')
    allocation_id = allocation_response['AllocationId']

    ec2.create_nat_gateway(SubnetId=subnet_id, AllocationId=allocation_id)

    credentials = {
        'aws_access_key_id': 'testing',
        'aws_secret_access_key': 'testing',
        'aws_session_token': 'testing'
    }

    count = scan_nat_gateways(credentials, 'us-east-1')
    assert count == 1


@mock_ec2
def test_scan_nat_gateways_multiple():
    """Test scanning with multiple NAT Gateways."""
    ec2 = boto3.client('ec2', region_name='us-east-1')

    vpc_response = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc_response['Vpc']['VpcId']

    subnet1_response = ec2.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')
    subnet1_id = subnet1_response['Subnet']['SubnetId']

    subnet2_response = ec2.create_subnet(VpcId=vpc_id, CidrBlock='10.0.2.0/24')
    subnet2_id = subnet2_response['Subnet']['SubnetId']

    subnet3_response = ec2.create_subnet(VpcId=vpc_id, CidrBlock='10.0.3.0/24')
    subnet3_id = subnet3_response['Subnet']['SubnetId']

    allocation1 = ec2.allocate_address(Domain='vpc')
    allocation2 = ec2.allocate_address(Domain='vpc')
    allocation3 = ec2.allocate_address(Domain='vpc')

    ec2.create_nat_gateway(SubnetId=subnet1_id, AllocationId=allocation1['AllocationId'])
    ec2.create_nat_gateway(SubnetId=subnet2_id, AllocationId=allocation2['AllocationId'])
    ec2.create_nat_gateway(SubnetId=subnet3_id, AllocationId=allocation3['AllocationId'])

    credentials = {
        'aws_access_key_id': 'testing',
        'aws_secret_access_key': 'testing',
        'aws_session_token': 'testing'
    }

    count = scan_nat_gateways(credentials, 'us-east-1')
    assert count == 3


@mock_ec2
def test_scan_nat_gateways_filters_deleted_state():
    """Test that deleted/deleting NAT Gateways are not counted."""
    ec2 = boto3.client('ec2', region_name='us-east-1')

    vpc_response = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc_response['Vpc']['VpcId']

    subnet_response = ec2.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')
    subnet_id = subnet_response['Subnet']['SubnetId']

    allocation1 = ec2.allocate_address(Domain='vpc')
    allocation2 = ec2.allocate_address(Domain='vpc')

    nat1 = ec2.create_nat_gateway(SubnetId=subnet_id, AllocationId=allocation1['AllocationId'])
    nat2 = ec2.create_nat_gateway(SubnetId=subnet_id, AllocationId=allocation2['AllocationId'])

    ec2.delete_nat_gateway(NatGatewayId=nat2['NatGateway']['NatGatewayId'])

    credentials = {
        'aws_access_key_id': 'testing',
        'aws_secret_access_key': 'testing',
        'aws_session_token': 'testing'
    }

    count = scan_nat_gateways(credentials, 'us-east-1')
    assert count == 1


@mock_ec2
def test_scan_nat_gateways_handles_exceptions():
    """Test error handling for API failures."""
    credentials = {
        'aws_access_key_id': 'invalid',
        'aws_secret_access_key': 'invalid',
        'aws_session_token': 'invalid'
    }

    count = scan_nat_gateways(credentials, 'invalid-region')
    assert count == 0
