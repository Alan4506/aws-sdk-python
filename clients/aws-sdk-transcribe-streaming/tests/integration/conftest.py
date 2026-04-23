# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Pytest fixtures for Transcribe Streaming integration tests.

Creates and tears down an IAM role and S3 bucket needed for medical scribe
integration tests once per test session. The ``healthscribe_resources``
fixture provides the role ARN and bucket name.
"""

import json
import time
import uuid
from typing import Any

import boto3
import pytest

REGION = "us-east-1"
_UNIQUE_SUFFIX = uuid.uuid4().hex
ROLE_NAME = f"HealthScribeIntegTestRole-{_UNIQUE_SUFFIX}"
BUCKET_NAME = f"healthscribe-integ-test-{_UNIQUE_SUFFIX}"


def _create_iam_role(iam_client: Any, role_name: str, bucket_name: str) -> None:
    """Create an IAM role with S3 PutObject access for Transcribe Streaming."""
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": ["transcribe.streaming.amazonaws.com"]},
                "Action": "sts:AssumeRole",
            }
        ],
    }

    try:
        iam_client.create_role(
            RoleName=role_name, AssumeRolePolicyDocument=json.dumps(trust_policy)
        )
    except iam_client.exceptions.EntityAlreadyExistsException:
        pass

    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": ["s3:PutObject"],
                "Resource": [
                    f"arn:aws:s3:::{bucket_name}",
                    f"arn:aws:s3:::{bucket_name}/*",
                ],
                "Effect": "Allow",
            }
        ],
    }

    iam_client.put_role_policy(
        RoleName=role_name,
        PolicyName="HealthScribeS3Access",
        PolicyDocument=json.dumps(permissions_policy),
    )


def _create_healthscribe_resources() -> tuple[str, str]:
    """Create an IAM role and S3 bucket for medical scribe tests.

    Returns:
        Tuple of (role_arn, bucket_name).
    """
    iam = boto3.client("iam")
    s3 = boto3.client("s3", region_name=REGION)
    sts = boto3.client("sts")

    account_id = sts.get_caller_identity()["Account"]

    s3.create_bucket(Bucket=BUCKET_NAME)
    _create_iam_role(iam, ROLE_NAME, BUCKET_NAME)

    # Wait for IAM role to propagate across services.
    time.sleep(10)

    role_arn = f"arn:aws:iam::{account_id}:role/{ROLE_NAME}"
    return role_arn, BUCKET_NAME


def _delete_healthscribe_resources() -> None:
    """Delete the IAM role and S3 bucket created for tests."""
    iam = boto3.client("iam")

    # Delete bucket and all its objects
    bucket = boto3.resource("s3").Bucket(BUCKET_NAME)
    try:
        bucket.objects.all().delete()
        bucket.delete()
    except bucket.meta.client.exceptions.NoSuchBucket:
        pass

    # Delete inline policy then role
    try:
        iam.delete_role_policy(RoleName=ROLE_NAME, PolicyName="HealthScribeS3Access")
    except iam.exceptions.NoSuchEntityException:
        pass

    try:
        iam.delete_role(RoleName=ROLE_NAME)
    except iam.exceptions.NoSuchEntityException:
        pass


@pytest.fixture(scope="session")
def healthscribe_resources():
    """Create HealthScribe resources for the test session and delete them after."""
    role_arn, bucket_name = _create_healthscribe_resources()
    yield role_arn, bucket_name
    _delete_healthscribe_resources()
