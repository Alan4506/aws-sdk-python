# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test non-streaming output type handling."""

import uuid

from aws_sdk_lex_runtime_v2.models import RecognizeTextInput, RecognizeTextOutput
from . import BOT_ID, BOT_ALIAS_ID, LOCALE_ID, create_lex_client


async def test_recognize_text() -> None:
    """Test non-streaming RecognizeText operation."""
    client = create_lex_client("us-east-1")
    response = await client.recognize_text(
        input=RecognizeTextInput(
            bot_id=BOT_ID,
            bot_alias_id=BOT_ALIAS_ID,
            locale_id=LOCALE_ID,
            session_id=str(uuid.uuid4()),
            text="Hello",
        )
    )

    assert isinstance(response, RecognizeTextOutput)
    assert response.session_id is not None

    # Verify session state with matched intent
    assert response.session_state is not None
    assert response.session_state.intent is not None
    assert response.session_state.intent.name == "Greeting"

    # Verify interpretations contain the matched intent
    assert response.interpretations is not None
    assert len(response.interpretations) > 0

    intent_names = [i.intent.name for i in response.interpretations if i.intent]
    assert "Greeting" in intent_names
    assert "FallbackIntent" in intent_names
