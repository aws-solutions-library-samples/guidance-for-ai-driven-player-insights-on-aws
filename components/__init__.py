""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import constants
import aws_cdk as cdk

from components.storage import Bucket
from components.endpoint import Endpoint
from components.pipeline import Pipeline
from components.notification import Notification
from constructs import Construct

class AutoMLStack(cdk.Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Initialize the `Bucket` component
        bucket = Bucket(self, "Bucket")

        # Initialize the SageMaker `Endpoint` deployment component
        endpoint = Endpoint(self, "Endpoint")

        # Initialize the AutoML `Pipeline` component
        pipeline = Pipeline(self, "Pipeline", endpoint=endpoint)

        # Initialize the S3 `Notification` to start the pipeline
        notification = Notification(self, "Notification", bucket=bucket)

        # Give the workflow execution role access to the solution bucket
        bucket.solution_bucket.grant_read_write(pipeline.workflow_role)

        # Give the notification function access to the solution bucket
        bucket.solution_bucket.grant_read_write(notification.function.role)

        # Add output for the data bucket name
        cdk.CfnOutput(
            self,
            "DataBucketName",
            value=bucket.solution_bucket.bucket_name
        )
