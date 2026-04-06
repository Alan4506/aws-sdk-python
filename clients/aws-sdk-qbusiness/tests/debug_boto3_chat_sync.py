# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "boto3",
# ]
# ///
"""
Debug script to see the raw HTTP response from Q Business using boto3.
Triggers a ValidationException by sending an invalid chatMode.

Usage:
    export QBUSINESS_APPLICATION_ID=your-app-id
    uv run tests/debug_boto3_chat_sync.py
"""

import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

boto3.set_stream_logger('', logging.DEBUG)

AWS_REGION = "us-east-1"
APPLICATION_ID = os.environ.get("QBUSINESS_APPLICATION_ID", "")

if not APPLICATION_ID:
    print("ERROR: Set QBUSINESS_APPLICATION_ID environment variable")
    exit(1)

client = boto3.client(
    "qbusiness",
    region_name=AWS_REGION,
    endpoint_url=f"https://qbusiness.{AWS_REGION}.api.aws",
)

try:
    response = client.chat_sync(
        applicationId=APPLICATION_ID,
        userMessage="Hello",
        chatMode="INVALID_MODE",
    )
    print(f"SUCCESS: {json.dumps(response, indent=2, default=str)}")
except ClientError as e:
    print(f"\n=== ClientError.response ===")
    print(json.dumps(e.response, indent=2, default=str))
