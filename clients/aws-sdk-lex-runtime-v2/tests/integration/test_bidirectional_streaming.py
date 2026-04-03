# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test bidirectional streaming event stream handling."""

import asyncio
import uuid

from smithy_core.aio.eventstream import DuplexEventStream

from aws_sdk_lex_runtime_v2.models import (
    StartConversationInput,
    StartConversationRequestEventStream,
    StartConversationRequestEventStreamConfigurationEvent,
    StartConversationRequestEventStreamTextInputEvent,
    StartConversationRequestEventStreamDisconnectionEvent,
    StartConversationResponseEventStream,
    StartConversationResponseEventStreamTextResponseEvent,
    StartConversationOutput,
    ConfigurationEvent,
    TextInputEvent,
    DisconnectionEvent,
)
from . import BOT_ID, BOT_ALIAS_ID, LOCALE_ID, create_lex_client


async def _send_events(
    stream: DuplexEventStream[
        StartConversationRequestEventStream,
        StartConversationResponseEventStream,
        StartConversationOutput,
    ],
) -> None:
    """Send configuration, text input, and disconnection events."""
    input_stream = stream.input_stream

    await input_stream.send(
        StartConversationRequestEventStreamConfigurationEvent(
            value=ConfigurationEvent(response_content_type="text/plain; charset=utf-8")
        )
    )

    await input_stream.send(
        StartConversationRequestEventStreamTextInputEvent(
            value=TextInputEvent(text="Hello")
        )
    )

    await asyncio.sleep(3)

    await input_stream.send(
        StartConversationRequestEventStreamDisconnectionEvent(
            value=DisconnectionEvent()
        )
    )

    await input_stream.close()


async def _receive_events(
    stream: DuplexEventStream[
        StartConversationRequestEventStream,
        StartConversationResponseEventStream,
        StartConversationOutput,
    ],
) -> tuple[bool, list[str]]:
    """Receive and collect output from the stream.

    Returns:
        Tuple of (got_text_response, messages)
    """
    got_text_response = False
    messages: list[str] = []

    _, output_stream = await stream.await_output()
    if output_stream is None:
        return got_text_response, messages

    async for event in output_stream:
        if isinstance(event, StartConversationResponseEventStreamTextResponseEvent):
            got_text_response = True
            if event.value.messages:
                for msg in event.value.messages:
                    if msg.content:
                        messages.append(msg.content)

    return got_text_response, messages


async def test_start_conversation() -> None:
    """Test bidirectional streaming StartConversation operation."""
    client = create_lex_client("us-east-1")

    stream = await client.start_conversation(
        input=StartConversationInput(
            bot_id=BOT_ID,
            bot_alias_id=BOT_ALIAS_ID,
            locale_id=LOCALE_ID,
            session_id=str(uuid.uuid4()),
            conversation_mode="TEXT",
        )
    )

    results = await asyncio.gather(_send_events(stream), _receive_events(stream))

    got_text_response, messages = results[1]
    assert got_text_response, "Expected to receive a TextResponse event"
    assert len(messages) > 0, "Expected at least one message in the response"
