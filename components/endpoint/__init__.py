""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import os
import constants
import aws_cdk as cdk
import aws_cdk.aws_lambda as _lambda
import aws_cdk.aws_iam as _iam

from constructs import Construct

class Endpoint(Construct):

    def __init__(self, scope: Construct, id: str) -> None:
        super().__init__(scope, id)

        # Define the Lambda Function to deploy the best model
        self.function = _lambda.Function(
            self,
            "EndpointFunction",
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
            timeout=cdk.Duration.seconds(amount=60)
        )

        # Add necessary permissions to create the Endpoint
        self.function.add_to_role_policy(
            _iam.PolicyStatement(
                sid="EndpointPermissions",
                actions=[
                    "sagemaker:CreateEndpointConfig",
                    "sagemaker:CreateEndpoint",
                    "sagemaker:UpdateEndpoint"
                ],
                effect=_iam.Effect.ALLOW,
                resources=[
                    f"arn:{cdk.Aws.PARTITION}:sagemaker:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:endpoint/{constants.WORKLOAD_NAME}*",
                    f"arn:{cdk.Aws.PARTITION}:sagemaker:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:endpoint/{constants.WORKLOAD_NAME.lower()}*",
                    f"arn:{cdk.Aws.PARTITION}:sagemaker:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:endpoint-config/{constants.WORKLOAD_NAME.lower()}*",
                    f"arn:{cdk.Aws.PARTITION}:sagemaker:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:endpoint-config/{constants.WORKLOAD_NAME}*"
                ]
            )
        )
        self.function.add_to_role_policy(
            _iam.PolicyStatement(
                sid="AddTagsPermission",
                actions=["sagemaker:AddTags"],
                effect=_iam.Effect.ALLOW,
                resources=["*"]
            )
        )
