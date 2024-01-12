""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import os
import constants
import aws_cdk as cdk
import aws_cdk.aws_s3 as _s3

from constructs import Construct

class Bucket(Construct):

    def __init__(self, scope: Construct, id: str) -> None:
        super().__init__(scope, id)

        # Define the default S3 data bucket for the solution
        self.solution_bucket = _s3.Bucket(
            self,
            "SolutionBucket",
            bucket_name=f"{constants.WORKLOAD_NAME.lower()}-data-{cdk.Aws.REGION}-{cdk.Aws.ACCOUNT_ID}",
            removal_policy=cdk.RemovalPolicy.RETAIN,
            versioned=True,
            encryption=_s3.BucketEncryption.S3_MANAGED
        )
