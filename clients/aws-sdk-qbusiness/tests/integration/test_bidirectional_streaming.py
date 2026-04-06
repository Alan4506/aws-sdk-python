# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test bidirectional event stream handling for the Chat API."""

import asyncio

import pytest
from smithy_core.aio.eventstream import DuplexEventStream

from aws_sdk_qbusiness.models import (
    ChatInput,
    ChatInputStream,
    ChatInputStreamConfigurationEvent,
    ChatInputStreamEndOfInputEvent,
    ChatInputStreamTextEvent,
    ChatOutput,
    ChatOutputStream,
    ChatOutputStreamTextEvent,
    ConfigurationEvent,
    EndOfInputEvent,
    TextInputEvent,
)

from . import APPLICATION_ID, AWS_REGION, create_qbusiness_client

MESSAGE = "What is Amazon Q Business?"


async def _send_chat_events(
    stream: DuplexEventStream[ChatInputStream, ChatOutputStream, ChatOutput],
) -> None:
    """Send chat input events: configuration, text message, end of input."""
    await stream.input_stream.send(
        ChatInputStreamConfigurationEvent(
            value=ConfigurationEvent(chat_mode="RETRIEVAL_MODE")
        )
    )

    await stream.input_stream.send(
        ChatInputStreamTextEvent(
            value=TextInputEvent(user_message=MESSAGE)
        )
    )

    await stream.input_stream.send(
        ChatInputStreamEndOfInputEvent(value=EndOfInputEvent())
    )

    # Small delay to ensure events are flushed before close.
    # See: aws-sdk-transcribe-streaming/examples/simple_file.py
    await asyncio.sleep(1)
    await stream.input_stream.close()


async def _receive_chat_output(
    stream: DuplexEventStream[ChatInputStream, ChatOutputStream, ChatOutput],
) -> tuple[bool, list[str]]:
    """Receive and collect chat output from the stream.

    Returns:
        Tuple of (got_text_events, collected_text)
    """
    got_text_events = False
    collected_text: list[str] = []

    _, output_stream = await stream.await_output()
    if output_stream is None:
        return got_text_events, collected_text

    # Read events from the output stream. Unknown event types from newer
    # service versions are automatically skipped by the framework.
    async for event in output_stream:
        if isinstance(event, ChatOutputStreamTextEvent):
            got_text_events = True
            if event.value.system_message:
                collected_text.append(event.value.system_message)

    return got_text_events, collected_text


@pytest.mark.skipif(
    not APPLICATION_ID,
    reason="QBUSINESS_APPLICATION_ID environment variable not set",
)
async def test_chat_bidirectional_streaming() -> None:
    """Test bidirectional streaming with text input and chat output.

    Note: client_token is manually provided because smithy-python does not yet
    auto-generate values for @idempotencyToken members.
    """
    import uuid

    qbusiness_client = create_qbusiness_client(AWS_REGION)

    stream = await qbusiness_client.chat(
        ChatInput(
            application_id=APPLICATION_ID,
            client_token=str(uuid.uuid4()),
        )
    )

    results = await asyncio.gather(
        _send_chat_events(stream), _receive_chat_output(stream)
    )
    got_text_events, collected_text = results[1]

    assert got_text_events, "Expected to receive text output events"
    assert len(collected_text) > 0, "Expected non-empty text response"
