# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test non-streaming output type handling."""

import uuid

import pytest

from aws_sdk_qbusiness.models import (
    ChatSyncInput,
    ChatSyncOutput,
    ListApplicationsInput,
    ListApplicationsOutput,
)

from . import APPLICATION_ID, AWS_REGION, create_qbusiness_client


async def test_list_applications() -> None:
    """Test non-streaming list operation."""
    qbusiness_client = create_qbusiness_client(AWS_REGION)

    response = await qbusiness_client.list_applications(
        ListApplicationsInput()
    )

    assert isinstance(response, ListApplicationsOutput)
    if response.applications is not None:
        assert isinstance(response.applications, list)


@pytest.mark.skipif(
    not APPLICATION_ID,
    reason="QBUSINESS_APPLICATION_ID environment variable not set",
)
async def test_chat_sync() -> None:
    """Test non-streaming ChatSync operation.

    Note: client_token is manually provided because smithy-python does not yet
    auto-generate values for @idempotencyToken members.
    """
    qbusiness_client = create_qbusiness_client(AWS_REGION)

    response = await qbusiness_client.chat_sync(
        ChatSyncInput(
            application_id=APPLICATION_ID,
            user_message="Hello",
            client_token=str(uuid.uuid4()),
        )
    )

    assert isinstance(response, ChatSyncOutput)
    assert response.system_message is not None
    assert isinstance(response.system_message, str)
    assert len(response.system_message) > 0
    assert response.conversation_id is not None


@pytest.mark.skipif(
    not APPLICATION_ID,
    reason="QBUSINESS_APPLICATION_ID environment variable not set",
)
def test_chat_sync_boto3() -> None:
    """Test non-streaming ChatSync operation using boto3 for comparison."""
    import boto3

    client = boto3.client(
        "qbusiness",
        region_name=AWS_REGION,
        endpoint_url=f"https://qbusiness.{AWS_REGION}.api.aws",
    )

    # boto3 auto-generates clientToken for @idempotencyToken fields
    response = client.chat_sync(
        applicationId=APPLICATION_ID,
        userMessage="Hello",
    )

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert "systemMessage" in response
    assert isinstance(response["systemMessage"], str)
    assert "conversationId" in response
