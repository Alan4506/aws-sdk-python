#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Demo: Using the Q Business Chat streaming API.

Usage:
    source smithy-python/.venv/bin/activate
    export QBUSINESS_APPLICATION_ID=<your-app-id>
    python tests/demo_chat.py
"""

import asyncio
import os
import sys
import uuid

from smithy_aws_core.identity import EnvironmentCredentialsResolver

from aws_sdk_qbusiness.client import QBusinessClient
from aws_sdk_qbusiness.config import Config
from aws_sdk_qbusiness.models import (
    ChatInput,
    ChatInputStreamConfigurationEvent,
    ChatInputStreamEndOfInputEvent,
    ChatInputStreamTextEvent,
    ChatOutputStreamMetadataEvent,
    ChatOutputStreamTextEvent,
    ConfigurationEvent,
    EndOfInputEvent,
    TextInputEvent,
)

APPLICATION_ID = os.environ.get("QBUSINESS_APPLICATION_ID", "")
REGION = "us-east-1"


async def main():
    if not APPLICATION_ID:
        print("Set QBUSINESS_APPLICATION_ID env var")
        sys.exit(1)

    message = input("You: ")

    client = QBusinessClient(
        config=Config(
            endpoint_uri=f"https://qbusiness.{REGION}.api.aws",
            region=REGION,
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
        )
    )

    stream = await client.chat(
        ChatInput(
            application_id=APPLICATION_ID,
            client_token=str(uuid.uuid4()),
        )
    )

    async def send():
        await stream.input_stream.send(
            ChatInputStreamConfigurationEvent(
                value=ConfigurationEvent(chat_mode="RETRIEVAL_MODE")
            )
        )
        await stream.input_stream.send(
            ChatInputStreamTextEvent(value=TextInputEvent(user_message=message))
        )
        await stream.input_stream.send(
            ChatInputStreamEndOfInputEvent(value=EndOfInputEvent())
        )
        # Small delay to ensure events are flushed before close
        await asyncio.sleep(1)
        await stream.input_stream.close()

    async def receive():
        _, output_stream = await stream.await_output()
        if output_stream is None:
            print("No response received.")
            return

        print("Q: ", end="", flush=True)
        async for event in output_stream:
            if isinstance(event, ChatOutputStreamTextEvent):
                if event.value.system_message:
                    print(event.value.system_message, end="", flush=True)
            elif isinstance(event, ChatOutputStreamMetadataEvent):
                print()

    await asyncio.gather(send(), receive())


if __name__ == "__main__":
    asyncio.run(main())
