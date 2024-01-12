""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import boto3
import constants
import aws_cdk as cdk
import aws_cdk.aws_sagemaker as _sagemaker
import aws_cdk.aws_iam as _iam

from components.endpoint import Endpoint
from components.pipeline.workflow import get_sagemaker_pipeline
from botocore.exceptions import ClientError
from constructs import Construct

class Pipeline(Construct):

    def __init__(self, scope: Construct, id: str, *, endpoint: Endpoint, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Get the SageMaker Execution Role for the Domain
        workflow_role_arn = self._get_execution_role()
        self.workflow_role = _iam.Role.from_role_arn(
            self,
            "WorkflowRole",
            role_arn=workflow_role_arn
        )

        # Add Pipeline Integrations and Lambda capabilities to the SageMaker Domain Execution Role
        self.workflow_role.attach_inline_policy(
            policy=_iam.Policy(
                self,
                "EndpointLambdaPolicy",
                document=_iam.PolicyDocument(
                    assign_sids=True,
                    statements=[
                        _iam.PolicyStatement(
                            actions=["lambda:InvokeFunction"],
                            effect=_iam.Effect.ALLOW,
                            resources=[endpoint.function.function_arn]
                        )
                    ]
                )
            )
        )

        # Get the SageMaker Pipeline definition
        sagemaker_pipeline = get_sagemaker_pipeline(
            role=self.workflow_role.role_arn,
            # default_bucket=bucket.solution_bucket.bucket_name,
            lambda_arn=endpoint.function.function_arn,
            evaluation_threshold=constants.PERFORMANCE_THRESHOLD,
            model_package_group_name=f"{constants.WORKLOAD_NAME}PackageGroup"
        )

        # Define the SageMaker Pipeline L1 construct
        self.automl_workflow = _sagemaker.CfnPipeline(
            self,
            "AutoMLPipeline",
            pipeline_name=f"{constants.WORKLOAD_NAME}-AutoMLPipeline",
            role_arn=self.workflow_role.role_arn,
            pipeline_description=f"SageMaker AutoML Pipeline for {constants.WORKLOAD_NAME}",
            pipeline_definition={
                "PipelineDefinitionBody": sagemaker_pipeline.definition()
            },
            tags=[
                cdk.CfnTag(
                    key="WorkloadName",
                    value=constants.WORKLOAD_NAME
                )
            ]
        )


    @staticmethod
    # Static method to get the SageMaker Execution Role for the SageMaker Studio Domain
    def _get_execution_role() -> str:
        client = boto3.client("sagemaker")
        try:
            domain = client.describe_domain(
                DomainId=constants.SM_DOMAIN_ID
            )
            return domain["DefaultUserSettings"]["ExecutionRole"]
        except ClientError as e:
            message = e.response["Error"]["Message"]
            raise Exception(message)
