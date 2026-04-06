# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "boto3",
# ]
# ///
#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Setup script to create AWS resources for Q Business integration tests.

Creates a Q Business application with anonymous access. This approach does not
require IAM Identity Center or an external identity provider, and allows Chat
and ChatSync API calls with standard IAM credentials.

Note:
    This script is intended for local testing only and should not be used for
    production setups.

Usage:
    uv run tests/setup_resources.py
"""

import time

import boto3


def wait_for_application(qbusiness, app_id: str) -> None:
    """Wait for application to become ACTIVE."""
    print("Waiting for application to become ACTIVE...")
    for _ in range(30):
        resp = qbusiness.get_application(applicationId=app_id)
        status = resp.get("status", "")
        if status == "ACTIVE":
            print("Application is ACTIVE")
            return
        print(f"  Status: {status}")
        time.sleep(10)
    raise RuntimeError("Application did not become ACTIVE within timeout")


def setup_qbusiness_resources() -> str:
    region = "us-east-1"
    qbusiness = boto3.client("qbusiness", region_name=region)

    # Reuse existing application if it exists
    app_id = None
    resp = qbusiness.list_applications()
    for app in resp.get("applications", []):
        if app.get("displayName") == "sdk-integration-test":
            app_id = app["applicationId"]
            print(f"Reusing existing application: {app_id}")
            break

    if app_id is None:
        resp = qbusiness.create_application(
            displayName="sdk-integration-test",
            description="Integration test application for aws-sdk-python",
            identityType="ANONYMOUS",
        )
        app_id = resp["applicationId"]
        print(f"Created application: {app_id}")
        wait_for_application(qbusiness, app_id)

    return app_id


if __name__ == "__main__":
    app_id = setup_qbusiness_resources()

    print("\nSetup complete. Export this environment variable before running tests:")
    print(f"export QBUSINESS_APPLICATION_ID={app_id}")
