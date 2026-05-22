# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Pytest fixtures for ConnectHealth integration tests.

Creates and tears down a ConnectHealth Domain with an ACTIVE Subscription
plus an S3 bucket once per test session. The ``connecthealth_resources``
fixture provides ``(domain_id, subscription_id, output_s3_uri)``.
"""

import uuid
from typing import Any

import boto3
import pytest
from botocore.waiter import WaiterModel, create_waiter_with_client

from . import REGION

# Tags applied to all resources so orphaned resources from interrupted
# test runs can be discovered and cleaned up.
_TAGS = [{"Key": "Purpose", "Value": "IntegTest"}]

_WAITER_CONFIG = {
    "version": 2,
    "waiters": {
        "DomainActive": {
            "operation": "GetDomain",
            "delay": 5,
            "maxAttempts": 60,
            "acceptors": [
                {
                    "matcher": "path",
                    "expected": "ACTIVE",
                    "argument": "status",
                    "state": "success",
                },
                {
                    "matcher": "path",
                    "expected": "DELETING",
                    "argument": "status",
                    "state": "failure",
                },
                {
                    "matcher": "path",
                    "expected": "DELETED",
                    "argument": "status",
                    "state": "failure",
                },
            ],
        },
        "SubscriptionActive": {
            "operation": "GetSubscription",
            "delay": 5,
            "maxAttempts": 60,
            "acceptors": [
                {
                    "matcher": "path",
                    "expected": "ACTIVE",
                    "argument": "subscription.status",
                    "state": "success",
                },
                {
                    "matcher": "path",
                    "expected": "DELETED",
                    "argument": "subscription.status",
                    "state": "failure",
                },
            ],
        },
        "SubscriptionInactive": {
            "operation": "GetSubscription",
            "delay": 5,
            "maxAttempts": 60,
            "acceptors": [
                {
                    "matcher": "path",
                    "expected": "INACTIVE",
                    "argument": "subscription.status",
                    "state": "success",
                },
                {
                    "matcher": "path",
                    "expected": "DELETED",
                    "argument": "subscription.status",
                    "state": "failure",
                },
            ],
        },
    },
}
_waiter_model = WaiterModel(_WAITER_CONFIG)


def _create_connecthealth_resources(
    s3_client: Any,
    connecthealth_client: Any,
    domain_name: str,
    bucket_name: str,
) -> tuple[str, str]:
    """Create an S3 bucket, ConnectHealth Domain, and ACTIVE Subscription.

    Args:
        s3_client: A boto3 S3 client.
        connecthealth_client: A boto3 ConnectHealth client.
        domain_name: The name of the Domain to create.
        bucket_name: The name of the S3 bucket to create.

    Returns:
        Tuple of (domain_id, subscription_id).
    """
    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_bucket_tagging(Bucket=bucket_name, Tagging={"TagSet": _TAGS})

    response = connecthealth_client.create_domain(
        name=domain_name,
        tags={t["Key"]: t["Value"] for t in _TAGS},
    )
    domain_id = response["domainId"]
    create_waiter_with_client(
        "DomainActive", _waiter_model, connecthealth_client
    ).wait(domainId=domain_id)

    response = connecthealth_client.create_subscription(domainId=domain_id)
    subscription_id = response["subscriptionId"]
    create_waiter_with_client(
        "SubscriptionActive", _waiter_model, connecthealth_client
    ).wait(domainId=domain_id, subscriptionId=subscription_id)

    return domain_id, subscription_id


def _delete_connecthealth_resources(
    s3_client: Any,
    connecthealth_client: Any,
    domain_id: str | None,
    subscription_id: str | None,
    bucket_name: str,
) -> None:
    """Deactivate the Subscription, then delete the Domain and S3 bucket.

    Args:
        s3_client: A boto3 S3 client.
        connecthealth_client: A boto3 ConnectHealth client.
        domain_id: The Domain ID to delete, or None if creation failed.
        subscription_id: The Subscription ID to deactivate, or None if
            creation failed.
        bucket_name: The name of the S3 bucket to delete.
    """
    if domain_id and subscription_id:
        connecthealth_client.deactivate_subscription(
            domainId=domain_id, subscriptionId=subscription_id
        )
        create_waiter_with_client(
            "SubscriptionInactive", _waiter_model, connecthealth_client
        ).wait(domainId=domain_id, subscriptionId=subscription_id)

    if domain_id:
        connecthealth_client.delete_domain(domainId=domain_id)

    # Empty and delete the bucket
    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket_name):
            objects = page.get("Contents")
            if not objects:
                continue
            s3_client.delete_objects(
                Bucket=bucket_name,
                Delete={"Objects": [{"Key": o["Key"]} for o in objects]},
            )
        s3_client.delete_bucket(Bucket=bucket_name)
    except s3_client.exceptions.NoSuchBucket:
        pass


@pytest.fixture(scope="session")
def connecthealth_resources():
    """Create ConnectHealth resources for the test session and delete them after."""
    unique_suffix = uuid.uuid4().hex[:16]
    domain_name = f"integ-test-connecthealth-domain-{unique_suffix}"
    bucket_name = f"integ-test-connecthealth-bucket-{unique_suffix}"

    s3_client = boto3.client("s3", region_name=REGION)
    connecthealth_client = boto3.client("connecthealth", region_name=REGION)

    domain_id = None
    subscription_id = None
    try:
        domain_id, subscription_id = _create_connecthealth_resources(
            s3_client, connecthealth_client, domain_name, bucket_name
        )
        output_s3_uri = f"s3://{bucket_name}/clinical-notes/"
        yield domain_id, subscription_id, output_s3_uri
    finally:
        _delete_connecthealth_resources(
            s3_client, connecthealth_client, domain_id, subscription_id, bucket_name
        )
