# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Pytest fixtures for Q Business integration tests.

Creates and tears down a Q Business application, an index,
and a retriever once per test session. All integration tests
receive the application_id via the ``qbusiness_app`` fixture.
"""

import uuid

import boto3
import pytest
from botocore.waiter import WaiterModel, create_waiter_with_client

from . import REGION

_UNIQUE_SUFFIX = uuid.uuid4().hex
APP_NAME = f"smithy-python-integ-test-{_UNIQUE_SUFFIX}"
INDEX_NAME = "integ-test-index"
RETRIEVER_NAME = "integ-test-retriever"

# Custom waiter configs for Q Business resources.
# Q Business does not provide built-in boto3 waiters.
_WAITER_CONFIG = {
    "version": 2,
    "waiters": {
        "ApplicationActive": {
            "operation": "GetApplication",
            "delay": 10,
            "maxAttempts": 30,
            "acceptors": [
                {
                    "matcher": "path",
                    "expected": "ACTIVE",
                    "argument": "status",
                    "state": "success",
                },
                {
                    "matcher": "path",
                    "expected": "FAILED",
                    "argument": "status",
                    "state": "failure",
                },
                {
                    "matcher": "path",
                    "expected": "DELETING",
                    "argument": "status",
                    "state": "failure",
                },
            ],
        },
        "IndexActive": {
            "operation": "GetIndex",
            "delay": 10,
            "maxAttempts": 30,
            "acceptors": [
                {
                    "matcher": "path",
                    "expected": "ACTIVE",
                    "argument": "status",
                    "state": "success",
                },
                {
                    "matcher": "path",
                    "expected": "FAILED",
                    "argument": "status",
                    "state": "failure",
                },
                {
                    "matcher": "path",
                    "expected": "DELETING",
                    "argument": "status",
                    "state": "failure",
                },
            ],
        },
        "RetrieverActive": {
            "operation": "GetRetriever",
            "delay": 10,
            "maxAttempts": 30,
            "acceptors": [
                {
                    "matcher": "path",
                    "expected": "ACTIVE",
                    "argument": "status",
                    "state": "success",
                },
                {
                    "matcher": "path",
                    "expected": "FAILED",
                    "argument": "status",
                    "state": "failure",
                },
            ],
        },
    },
}

_waiter_model = WaiterModel(_WAITER_CONFIG)


def _create_qbusiness_app() -> str:
    """Create a Q Business application with index and retriever.

    Returns:
        The application ID.
    """
    qbusiness = boto3.client("qbusiness", region_name=REGION)

    # Create application
    resp = qbusiness.create_application(displayName=APP_NAME, identityType="ANONYMOUS")
    app_id = resp["applicationId"]
    create_waiter_with_client("ApplicationActive", _waiter_model, qbusiness).wait(
        applicationId=app_id
    )

    # Create index
    resp = qbusiness.create_index(applicationId=app_id, displayName=INDEX_NAME)
    index_id = resp["indexId"]
    create_waiter_with_client("IndexActive", _waiter_model, qbusiness).wait(
        applicationId=app_id, indexId=index_id
    )

    # Create retriever
    resp = qbusiness.create_retriever(
        applicationId=app_id,
        displayName=RETRIEVER_NAME,
        type="NATIVE_INDEX",
        configuration={"nativeIndexConfiguration": {"indexId": index_id}},
    )
    retriever_id = resp["retrieverId"]
    create_waiter_with_client("RetrieverActive", _waiter_model, qbusiness).wait(
        applicationId=app_id, retrieverId=retriever_id
    )

    return app_id


def _delete_qbusiness_app(app_id: str) -> None:
    """Delete a Q Business application.

    Args:
        app_id: The application ID to delete.
    """
    qbusiness = boto3.client("qbusiness", region_name=REGION)
    qbusiness.delete_application(applicationId=app_id)


@pytest.fixture(scope="session")
def qbusiness_app():
    """Create a Q Business application for the test session and delete it after."""
    app_id = _create_qbusiness_app()
    yield app_id
    _delete_qbusiness_app(app_id)
