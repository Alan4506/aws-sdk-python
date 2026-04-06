# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

from smithy_aws_core.identity import EnvironmentCredentialsResolver

from aws_sdk_qbusiness.client import QBusinessClient
from aws_sdk_qbusiness.config import Config

AWS_REGION = "us-east-1"
APPLICATION_ID = os.environ.get("QBUSINESS_APPLICATION_ID", "")


def create_qbusiness_client(region: str) -> QBusinessClient:
    """Helper to create a QBusinessClient for a given region."""
    return QBusinessClient(
        config=Config(
            endpoint_uri=f"https://qbusiness.{region}.api.aws",
            region=region,
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
        )
    )
