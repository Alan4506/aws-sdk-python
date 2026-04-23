# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Pytest fixtures for Lex Runtime V2 integration tests.

Creates and tears down a Lex V2 bot with a Greeting intent once per
test session. All integration tests receive the bot_id via the
``lex_bot`` fixture.
"""

import json
import uuid

import boto3
import pytest

from . import LOCALE_ID, REGION

_UNIQUE_SUFFIX = uuid.uuid4().hex
ROLE_NAME = f"LexRuntimeV2IntegTestRole-{_UNIQUE_SUFFIX}"
BOT_NAME = f"smithy-python-integ-test-bot-{_UNIQUE_SUFFIX}"


def _create_lex_bot() -> str:
    """Create a Lex V2 bot with a Greeting intent.

    Returns:
        The bot ID.
    """
    iam = boto3.client("iam")
    lex = boto3.client("lexv2-models", region_name=REGION)
    sts = boto3.client("sts")

    account_id = sts.get_caller_identity()["Account"]
    role_arn = f"arn:aws:iam::{account_id}:role/{ROLE_NAME}"

    # Create IAM role for the bot
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lexv2.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    try:
        iam.create_role(
            RoleName=ROLE_NAME, AssumeRolePolicyDocument=json.dumps(trust_policy)
        )
    except iam.exceptions.EntityAlreadyExistsException:
        pass

    # Create bot
    response = lex.create_bot(
        botName=BOT_NAME,
        roleArn=role_arn,
        dataPrivacy={"childDirected": False},
        # 5-minute idle timeout is sufficient for integration tests.
        idleSessionTTLInSeconds=300,
    )
    bot_id = response["botId"]
    lex.get_waiter("bot_available").wait(botId=bot_id)

    # Create locale
    lex.create_bot_locale(
        botId=bot_id,
        botVersion="DRAFT",
        localeId=LOCALE_ID,
        # Required field. Confidence threshold (0-1) that determines when Lex
        # inserts AMAZON.FallbackIntent into the interpretations list.
        # 0.40 is a reasonable value for a simple test bot.
        nluIntentConfidenceThreshold=0.40,
    )
    lex.get_waiter("bot_locale_created").wait(
        botId=bot_id, botVersion="DRAFT", localeId=LOCALE_ID
    )

    # Create intent
    lex.create_intent(
        intentName="Greeting",
        botId=bot_id,
        botVersion="DRAFT",
        localeId=LOCALE_ID,
        sampleUtterances=[
            {"utterance": "Hello"},
            {"utterance": "Hi"},
            {"utterance": "Hey"},
        ],
        intentClosingSetting={
            "closingResponse": {
                "messageGroups": [
                    {
                        "message": {
                            "plainTextMessage": {"value": "Hello! How can I help you?"}
                        }
                    }
                ]
            },
            "active": True,
        },
    )

    # Build locale
    lex.build_bot_locale(botId=bot_id, botVersion="DRAFT", localeId=LOCALE_ID)
    lex.get_waiter("bot_locale_built").wait(
        botId=bot_id, botVersion="DRAFT", localeId=LOCALE_ID
    )

    return bot_id


def _delete_lex_bot(bot_id: str) -> None:
    """Delete a Lex V2 bot and its associated IAM role.

    Args:
        bot_id: The bot ID to delete.
    """
    lex = boto3.client("lexv2-models", region_name=REGION)
    iam = boto3.client("iam")

    lex.delete_bot(botId=bot_id, skipResourceInUseCheck=True)

    try:
        iam.delete_role(RoleName=ROLE_NAME)
    except iam.exceptions.NoSuchEntityException:
        pass


@pytest.fixture(scope="session")
def lex_bot():
    """Create a Lex bot for the test session and delete it after."""
    bot_id = _create_lex_bot()
    yield bot_id
    _delete_lex_bot(bot_id)
