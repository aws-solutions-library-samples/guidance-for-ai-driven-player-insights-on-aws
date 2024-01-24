""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import os
import time
import urllib.parse
import json
import boto3

from botocore.exceptions import ClientError
from aws_lambda_powertools import Tracer
from aws_lambda_powertools import Logger

tracer = Tracer()
logger = Logger()

@tracer.capture_lambda_handler
def lambda_handler(event, context):
    # print("Received event: " + json.dumps(event, indent=2)) # Debug
    pipeline_name = os.environ["PIPELINE_NAME"]
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]
    version_id = event["Records"][0]["s3"]["object"]["versionId"]
    try:
        logger.info("Starting SageMaker Pipeline Execution ...")
        sm_client = boto3.client("sagemaker")
        response = sm_client.start_pipeline_execution(
            PipelineName=pipeline_name,
            PipelineParameters=[
                {
                    "Name": "ExecutionVersion",
                    "Value": version_id
                },
                {
                    "Name": "DataUri",
                    "Value": f"s3://{bucket}/{key}"
                },
                {
                    "Name": "DataFile",
                    "Value": key.split("/")[-1]
                }
            ]
        )

        logger.info(f"Pipeline Execution ARN: {response['PipelineExecutionArn']}")
        return {
            "statusCode": 200,
            "body": response["PipelineExecutionArn"]
        }
        
    except ClientError as e:
        message = e.response["Error"]["Message"]
        raise Exception(message)
