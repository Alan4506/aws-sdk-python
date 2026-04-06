"""
Debug script to test ChatSync with full logging.

Usage:
    export QBUSINESS_APPLICATION_ID=your-app-id
    python tests/debug_chat_sync.py
"""

import asyncio
import logging
import os
import uuid

logging.basicConfig(level=logging.DEBUG)

from smithy_aws_core.identity import EnvironmentCredentialsResolver

from aws_sdk_qbusiness.client import QBusinessClient
from aws_sdk_qbusiness.config import Config
from aws_sdk_qbusiness.models import ChatSyncInput

AWS_REGION = "us-east-1"
APPLICATION_ID = os.environ.get("QBUSINESS_APPLICATION_ID", "")


async def main():
    if not APPLICATION_ID:
        print("ERROR: Set QBUSINESS_APPLICATION_ID environment variable")
        return

    client = QBusinessClient(
        config=Config(
            endpoint_uri=f"https://qbusiness.{AWS_REGION}.api.aws",
            region=AWS_REGION,
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
        )
    )

    try:
        response = await client.chat_sync(
            ChatSyncInput(
                application_id=APPLICATION_ID,
                user_message="Hello",
                client_token=str(uuid.uuid4()),
            )
        )
        print(f"\nSUCCESS:")
        print(f"  system_message: {response.system_message}")
        print(f"  conversation_id: {response.conversation_id}")
    except Exception as e:
        print(f"\nFAILED: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
