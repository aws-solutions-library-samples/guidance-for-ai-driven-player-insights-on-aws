""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

# SEE: https://github.com/aws/amazon-sagemaker-examples/blob/main/sagemaker-pipelines/tabular/automl-step/sagemaker_autopilot_pipelines_native_auto_ml_step.ipynb

import os
import boto3
import json
import sagemaker
import constants

from sagemaker import AutoML, AutoMLInput, MetricsSource, ModelMetrics, ModelPackage
from sagemaker.transformer import Transformer
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.processing import ProcessingOutput, ProcessingInput
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.parameters import ParameterFloat, ParameterInteger, ParameterString
from sagemaker.workflow.pipeline_context import PipelineSession
from sagemaker.workflow.properties import PropertyFile
from sagemaker.workflow.model_step import ModelStep
from sagemaker.workflow.functions import Join, JsonGet
from sagemaker.workflow.steps import ProcessingStep, TransformStep
from sagemaker.workflow.automl_step import AutoMLStep
from sagemaker.workflow.conditions import ConditionGreaterThanOrEqualTo
from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.lambda_step import LambdaStep, LambdaOutput, LambdaOutputTypeEnum
from sagemaker.workflow.fail_step import FailStep
from sagemaker.lambda_helper import Lambda


def get_pipeline_session(region: str) -> None:
    boto_session = boto3.Session(region_name=region)
    sagemaker_client = boto_session.client("sagemaker")
    return PipelineSession(
        boto_session=boto_session,
        sagemaker_client=sagemaker_client
    )


def get_sagemaker_pipeline(
    role: str,
    lambda_arn: str,
    model_package_group_name: str,
    evaluation_threshold: float
) -> None:

    # SageMaker session variables
    if role is None:
        raise("Execution Role is Required")
    pipeline_session = get_pipeline_session(region=constants.REGION)

    # Pipeline variables
    execution_version = ParameterString(name="ExecutionVersion", default_value="Test")
    instance_count = ParameterInteger(name="InstanceCount", default_value=1)
    instance_type = ParameterString(name="InstanceType", default_value="ml.m5.xlarge")
    max_runtime = ParameterInteger(name="MaxAutoMLRuntime", default_value=7200)  # max. AutoML training runtime: 2 hours
    model_approval_status = ParameterString(name="ModelApprovalStatus", default_value="Approved")
    metric_threshold = ParameterFloat(name="ModelRegistrationMetricThreshold", default_value=evaluation_threshold)
    data_uri = ParameterString(name="DataUri", default_value=f"s3://{pipeline_session.default_bucket()}/features.csv")
    data_file = ParameterString(name="DataFile", default_value="features.csv")
    evaluation_report = PropertyFile(name="evaluation", output_name="evaluation_metrics", path="evaluation_metrics.json")

    # Data preprocessing step
    preprocessor = SKLearnProcessor(
        role=role,
        framework_version="1.0-1",
        instance_count=instance_count,
        instance_type=instance_type.default_value,
        sagemaker_session=pipeline_session,
        base_job_name=f"{constants.WORKLOAD_NAME}/preprocessing",
        env={
            "TARGET_ATTRIBUTE": constants.TARGET_ATTRIBUTE
        }
    )
    preprocessing_step = ProcessingStep(
        name="DataPreprocessingStep",
        step_args=preprocessor.run(
            inputs=[
                ProcessingInput(
                    input_name="data",
                    source=data_uri,
                    destination="/opt/ml/processing/input"
                )
            ],
            outputs=[
                ProcessingOutput(
                    output_name="training",
                    source="/opt/ml/processing/output/training",
                    destination=Join(on="/", values=["s3:/", pipeline_session.default_bucket(), constants.WORKLOAD_NAME, execution_version, "training"])
                ),
                ProcessingOutput(
                    output_name="testing",
                    source="/opt/ml/processing/output/testing",
                    destination=Join(on="/", values=["s3:/", pipeline_session.default_bucket(), constants.WORKLOAD_NAME, execution_version, "testing"])
                )
            ],
            code=os.path.join(os.path.dirname(__file__), "code/preprocessing.py"),
            arguments=["--input-file", data_file]
        )
    )

    # AutoML training step
    automl = AutoML(
        role=role,
        target_attribute_name=constants.TARGET_ATTRIBUTE,
        sagemaker_session=pipeline_session,
        total_job_runtime_in_seconds=max_runtime,
        base_job_name=f"{constants.WORKLOAD_NAME}/training",
        mode="ENSEMBLING"  # Only `ENSEMBLING` mode is supported for native AutoML step integration in SageMaker Pipelines
    )
    automl_step = AutoMLStep(
        name="AutoMLTrainingStep",
        step_args=automl.fit(
            inputs=[
                AutoMLInput(
                    inputs=preprocessing_step.properties.ProcessingOutputConfig.Outputs["training"].S3Output.S3Uri,
                    target_attribute_name=constants.TARGET_ATTRIBUTE,
                    channel_type="training"
                )
            ]
        )
    )

    # Create SageMaker model from the best candidate
    best_model = automl_step.get_best_auto_ml_model(
        role=role,
        sagemaker_session=pipeline_session
    )
    create_model_args = best_model.create(instance_type=instance_type)
    model_step = ModelStep(
        "ModelCreationStep",
        step_args=create_model_args
    )

    # Run Batch Inference on the test dataset
    # NOTE: Ensure `test` dataset is not larger than 6MB in size
    batch_transformer = Transformer(
        model_name=model_step.properties.ModelName,
        instance_count=instance_count,
        instance_type=instance_type,
        base_transform_job_name=f"{constants.WORKLOAD_NAME}/batch-inference",
        output_path=Join(on="/", values=["s3:/", pipeline_session.default_bucket(), constants.WORKLOAD_NAME, execution_version, "transform"]),
        sagemaker_session=pipeline_session
    )
    batch_inference_step = TransformStep(
        name="InferenceTestingStep",
        step_args=batch_transformer.transform(
            data=Join(
                on="/",
                values=[
                    preprocessing_step.properties.ProcessingOutputConfig.Outputs["testing"].S3Output.S3Uri,
                    "x_test.csv"
                ]
            ),
            content_type="text/csv"
        )
    )

    # Evaluate the inference testing results against ground truth data to get the F1 score
    evaluator = SKLearnProcessor(
        role=role,
        framework_version="1.0-1",
        instance_count=instance_count,
        instance_type=instance_type,
        base_job_name=f"{constants.WORKLOAD_NAME}/evaluation",
        sagemaker_session=pipeline_session
    )
    evaluation_step = ProcessingStep(
        name="ModelEvaluationStep",
        step_args=evaluator.run(
            inputs=[
                ProcessingInput(
                    source=batch_inference_step.properties.TransformOutput.S3OutputPath,
                    destination="/opt/ml/processing/input/predictions"
                ),
                ProcessingInput(
                    source=Join(
                        on="/",
                        values=[
                            preprocessing_step.properties.ProcessingOutputConfig.Outputs["testing"].S3Output.S3Uri,
                            "y_test.csv"
                        ]
                    ),
                    destination="/opt/ml/processing/input/true_labels"
                )
            ],
            outputs=[
                ProcessingOutput(
                    output_name="evaluation_metrics",
                    source="/opt/ml/processing/evaluation",
                    destination=Join(
                        on="/",
                        values=[
                            "s3:/",
                            pipeline_session.default_bucket(),
                            constants.WORKLOAD_NAME,
                            execution_version,
                            "evaluation"
                        ]
                    )
                )
            ],
            code=os.path.join(os.path.dirname(__file__), "code/evaluation.py")
        ),
        property_files=[evaluation_report]
    )

    # Create Model Deployment Lambda Step
    deployment_step = LambdaStep(
        name="ModelDeploymentStep",
        lambda_func=Lambda(
            function_arn=lambda_arn
        ),
        inputs={
            "MODEL_NAME": model_step.properties.ModelName,
            "INSTANCE_TYPE": instance_type,
            "WORKLOAD_NAME": f"{constants.WORKLOAD_NAME}",
            "ENDPOINT_TYPE": constants.ENDPOINT_TYPE
        },
        outputs=[
            LambdaOutput(output_name="statusCode", output_type=LambdaOutputTypeEnum.String),
            LambdaOutput(output_name="body", output_type=LambdaOutputTypeEnum.String)
        ]
    )

    # Define the step for pipeline failure
    failure_step = FailStep(
        name="ModelEvaluationFailure",
        error_message=Join(
            on=" ",
            values=["Pipeline execution failure: Model Quality (F1 Score) is less than the specified Evaluation Threshold"]
        )
    )

    # Create Registration Step
    model_metrics = ModelMetrics(
        model_statistics=MetricsSource(
            s3_uri=automl_step.properties.BestCandidateProperties.ModelInsightsJsonReportPath,
            content_type="application/json"
        ),
        explainability=MetricsSource(
            s3_uri=automl_step.properties.BestCandidateProperties.ExplainabilityJsonReportPath,
            content_type="application/json"
        ),
    )
    step_register_model = ModelStep(
        name="ModelRegistrationStep",
        step_args=best_model.register(
            content_types=["text/csv"],
            response_types=["text/csv"],
            inference_instances=[instance_type],
            transform_instances=[instance_type],
            model_package_group_name=model_package_group_name,
            approval_status=model_approval_status,
            model_metrics=model_metrics
        )
    )

    # Create Conditional Registration/Deployment/Failure Step
    conditional_step = ConditionStep(
        name="ModelQualityCondition",
        conditions=[
            ConditionGreaterThanOrEqualTo(
                left=JsonGet(
                    step_name=evaluation_step.name,
                    property_file=evaluation_report,
                    json_path="classification_metrics.weighted_f1.value"
                ),
                right=metric_threshold
            )
        ],
        if_steps=[step_register_model, deployment_step],
        else_steps=[failure_step]
    )

    pipeline = Pipeline(
        name="AutoMLTrainingPipeline",
        parameters=[
            execution_version,
            instance_count,
            instance_type,
            max_runtime,
            model_approval_status,
            metric_threshold,
            data_uri,
            data_file
        ],
        steps=[
            preprocessing_step,
            automl_step,
            model_step,
            batch_inference_step,
            evaluation_step,
            conditional_step
        ],
        sagemaker_session=pipeline_session
    )

    # Create `definition.json` to debug the pipeline definition
    # with open("definition.json", "w") as f:
    #     json.dump(json.loads(pipeline.definition()), f, indent=4)

    return pipeline
    
