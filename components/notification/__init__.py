""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import os
import constants
import aws_cdk as cdk
import aws_cdk.aws_lambda as _lambda
import aws_cdk.aws_s3 as _s3
import aws_cdk.aws_s3_notifications as _notifications
import aws_cdk.aws_iam as _iam

from components.storage import Bucket
from constructs import Construct

class Notification(Construct):

    def __init__(self, scope: Construct, id: str, *, bucket: Bucket, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Define the Lambda Function to execute the AutoML workflow upon adding a new file
        self.function = _lambda.Function(
            self,
            "NotificationFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset(
                os.path.join(os.path.dirname(__file__), "runtime"),
                bundling=cdk.BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_11.bundling_image,
                    command=[
                        "bash", "-c", "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ]
                )
            ),
            handler="index.lambda_handler",
            timeout=cdk.Duration.seconds(amount=60),
            environment={
                "PIPELINE_NAME": f"{constants.WORKLOAD_NAME}-AutoMLPipeline"
            }
        )

        # Add the trigger using the `DATA_FILE` as the suffix
        notification = _notifications.LambdaDestination(self.function)
        notification.bind(self, bucket=bucket.solution_bucket)
        bucket.solution_bucket.add_object_created_notification(
            notification,
            _s3.NotificationKeyFilter(
                suffix=constants.DATA_FILE
            )
        )

        # Give the notification function access to invoke the automl workflow
        self.function.add_to_role_policy(
            _iam.PolicyStatement(
                sid="StartPipelinePermissions",
                actions=["sagemaker:StartPipelineExecution"],
                effect=_iam.Effect.ALLOW,
                resources=[
                    f"arn:{cdk.Aws.PARTITION}:sagemaker:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:pipeline/{constants.WORKLOAD_NAME.lower()}-automlpipeline",
                    f"arn:{cdk.Aws.PARTITION}:sagemaker:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:pipeline/{constants.WORKLOAD_NAME}-AutoMLPipeline"
                ]
            )
        )
