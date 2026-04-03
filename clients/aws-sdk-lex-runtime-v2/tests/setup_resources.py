# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "boto3",
# ]
# ///
#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Setup script to create AWS resources for Lex Runtime V2 integration tests.

Creates a simple Lex V2 bot with a Greeting intent for testing.

Note:
    This script is intended for local testing only and should not be used for
    production setups.

Usage:
    uv run tests/setup_resources.py
"""

import json
import time

import boto3


def create_lex_bot() -> tuple[str, str, str]:
    """Create a simple Lex V2 bot for testing.

    Returns:
        Tuple of (bot_id, bot_alias_id, locale_id)
    """
    region = "us-east-1"
    iam = boto3.client("iam")
    lex = boto3.client("lexv2-models", region_name=region)
    sts = boto3.client("sts")

    account_id = sts.get_caller_identity()["Account"]
    role_name = "LexRuntimeV2IntegrationTestRole"
    bot_name = "smithy-python-test-bot"
    locale_id = "en_US"

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
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
        )
    except iam.exceptions.EntityAlreadyExistsException:
        pass

    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"

    # Check if bot already exists
    existing_bots = lex.list_bots(
        filters=[{"name": "BotName", "values": [bot_name], "operator": "EQ"}]
    )
    if existing_bots["botSummaries"]:
        bot_id = existing_bots["botSummaries"][0]["botId"]
        print(f"Bot already exists: {bot_id}")
    else:
        response = lex.create_bot(
            botName=bot_name,
            roleArn=role_arn,
            dataPrivacy={"childDirected": False},
            idleSessionTTLInSeconds=300,
        )
        bot_id = response["botId"]
        print(f"Created bot: {bot_id}")
        _wait_for_bot(lex, bot_id)

    # Ensure locale exists
    try:
        locale_resp = lex.describe_bot_locale(
            botId=bot_id, botVersion="DRAFT", localeId=locale_id
        )
        locale_status = locale_resp["botLocaleStatus"]
        print(f"Locale status: {locale_status}")
    except lex.exceptions.ResourceNotFoundException:
        print("Creating locale...")
        lex.create_bot_locale(
            botId=bot_id,
            botVersion="DRAFT",
            localeId=locale_id,
            nluIntentConfidenceThreshold=0.40,
        )
        _wait_for_bot_locale(lex, bot_id, locale_id, target_status="NotBuilt")
        locale_status = "NotBuilt"

    # Create intent and build locale if not already built
    if locale_status != "Built":
        intent_name = "Greeting"
        existing_intents = lex.list_intents(
            botId=bot_id, botVersion="DRAFT", localeId=locale_id,
            filters=[{"name": "IntentName", "values": [intent_name], "operator": "EQ"}],
        )
        if not existing_intents["intentSummaries"]:
            print(f"Creating intent: {intent_name}")
            lex.create_intent(
                intentName=intent_name,
                botId=bot_id,
                botVersion="DRAFT",
                localeId=locale_id,
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
                                    "plainTextMessage": {
                                        "value": "Hello! How can I help you?"
                                    }
                                }
                            }
                        ],
                    },
                    "active": True,
                },
            )

        print("Building locale...")
        lex.build_bot_locale(
            botId=bot_id, botVersion="DRAFT", localeId=locale_id
        )
        _wait_for_bot_locale(lex, bot_id, locale_id, target_status="Built")

    # Use TSTALIASID (test alias, always available)
    bot_alias_id = "TSTALIASID"

    return bot_id, bot_alias_id, locale_id


def _wait_for_bot(lex, bot_id: str, timeout: int = 60) -> None:
    for _ in range(timeout // 5):
        response = lex.describe_bot(botId=bot_id)
        status = response["botStatus"]
        if status == "Available":
            return
        if status in ("Failed", "Deleting"):
            raise RuntimeError(f"Bot creation failed with status: {status}")
        time.sleep(5)
    raise TimeoutError("Bot did not become available")


def _wait_for_bot_locale(
    lex, bot_id: str, locale_id: str, target_status: str, timeout: int = 60
) -> None:
    for _ in range(timeout // 5):
        response = lex.describe_bot_locale(
            botId=bot_id, botVersion="DRAFT", localeId=locale_id
        )
        status = response["botLocaleStatus"]
        if status == target_status:
            return
        if status in ("Failed", "Deleting"):
            raise RuntimeError(f"Bot locale failed with status: {status}")
        time.sleep(5)
    raise TimeoutError(f"Bot locale did not reach {target_status}")


if __name__ == "__main__":
    bot_id, bot_alias_id, locale_id = create_lex_bot()

    print("\nSetup complete. Export this environment variable before running tests:")
    print(f"export LEX_BOT_ID={bot_id}")
