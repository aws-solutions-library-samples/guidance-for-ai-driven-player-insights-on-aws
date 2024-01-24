""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import json
import boto3
import time

from botocore.exceptions import ClientError
from aws_lambda_powertools import Tracer
from aws_lambda_powertools import Logger

logger = Logger()
tracer = Tracer()
sm_client = boto3.client("sagemaker")

@tracer.capture_lambda_handler
def lambda_handler(event, context):

    # The name of the model created in the Pipeline CreateModelStep
    current_time = time.strftime("%m-%d-%H-%M-%S", time.localtime())
    model_name = event["MODEL_NAME"]
    workload_name = event["WORKLOAD_NAME"]
    endpoint_config_name = f"{workload_name}-{current_time}"
    endpoint_name = f"{workload_name}-Endpoint"
    instance_type = event["INSTANCE_TYPE"]
    endpoint_type = event["ENDPOINT_TYPE"]
    response_body = {}

    try:
        # Create the SageMaker Endpoint Configuration, based on the current time
        logger.info("Creating Endpoint Config")
        if endpoint_type == "SERVERLESS": 
            response = sm_client.create_endpoint_config(
                EndpointConfigName=endpoint_config_name,
                ProductionVariants=[
                    {
                        "ModelName": model_name,
                        "VariantName": "AllTraffic",
                        "ServerlessConfig": {
                            "MemorySizeInMB": 4096,
                            "MaxConcurrency": 20
                        }
                    }
                ],
                Tags=[
                    {
                        "Key": "WorkloadName",
                        "Value": workload_name
                    }
                ]
            )
        elif endpoint_type == "HOSTED":
            response = sm_client.create_endpoint_config(
                EndpointConfigName=endpoint_config_name,
                ProductionVariants=[
                    {
                        "InstanceType": instance_type,
                        "InitialVariantWeight": 1,
                        "InitialInstanceCount": 1,
                        "ModelName": model_name,
                        "VariantName": "AllTraffic"
                    }
                ],
                Tags=[
                    {
                        "Key": "WorkloadName",
                        "Value": workload_name
                    }
                ]
            )
        else:
            raise Exception("Invalid Endpoint Type. Please spcify 'HOSTED' or 'SERVERLESS'")
        logger.info(f"Endpoint Config: {response['EndpointConfigArn']}")
        response_body["EndpointConfigArn"] = response["EndpointConfigArn"]

    except ClientError as e:
        message = e.response["Error"]["Message"]
        raise Exception(message)

    try:
        # Update the SageMaker Endpoint with the new configuration
        logger.info("Updating Existing Endpoint")
        response = sm_client.update_endpoint(
            EndpointName=endpoint_name,
            EndpointConfigName=endpoint_config_name
        )
        response_body["EndpointArn"] = response["EndpointArn"]
    except ClientError as e:
        logger.info(f"Existing Endpoint Not Found")
        logger.info(f"{e.response['Error']['Message']}") #Debug
        try:
            # Create the SageMaker Endpoint
            logger.info("Creating New Endpoint")
            response = sm_client.create_endpoint(
                EndpointName=endpoint_name,
                EndpointConfigName=endpoint_config_name,
                Tags=[
                    {
                        "Key": "WorkloadName",
                        "Value": workload_name
                    }
                ]
            )
            logger.info(f"Endpoint: {response['EndpointArn']}")
            response_body["EndpointArn"] = response["EndpointArn"]
        
        except ClientError as e:
            message = e.response["Error"]["Message"]
            raise Exception(message)

    return {
        "statusCode": 200,
        "body": json.dumps(response_body)
    }
