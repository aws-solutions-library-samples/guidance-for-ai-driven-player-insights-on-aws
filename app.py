#!/usr/bin/env python3

""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import boto3
import constants
import aws_cdk as cdk
from components import AutoMLStack


app = cdk.App()
AutoMLStack(
    app,
    f"{constants.WORKLOAD_NAME}-Stack",
    description="Guidance for AI-driven player insights on AWS (SO9401)",
    env=cdk.Environment(
        account=boto3.client("sts").get_caller_identity()["Account"],
        region=constants.REGION
    )
)
app.synth()
