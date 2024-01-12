""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import os
import pathlib
import argparse
import logging
import pandas as pd

from sklearn.model_selection import train_test_split

logger = logging.getLogger()
logger.setLevel(level=logging.INFO)
logger.addHandler(logging.StreamHandler())
training_output_dir = "/opt/ml/processing/output/training"
target_attribute = os.environ["TARGET_ATTRIBUTE"]


if __name__ == "__main__":
    logger.debug("Starting Preprocessing ...")
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", type=str, required=True)
    args = parser.parse_args()
    logger.info(f"Reading File: {args.input_file}")

    # Read csv as pandas DataFrame
    input_data_path = os.path.join("/opt/ml/processing/input", args.input_file)
    df = pd.read_csv(input_data_path)
    
    # Capture headings
    headers = list(df.columns.values)
    
    # remove the target attribute from the list
    headers.pop(headers.index(target_attribute))
    column_names = headers + [target_attribute]

    # Create a new DataFrame with the target attribute as the last column
    df = df[column_names]
    logger.debug("Shape of the data is:", df.shape)

    # Split the data (80/20)
    train, test = train_test_split(df, test_size=0.2)

    # Save training data files 
    pathlib.Path(training_output_dir).mkdir(parents=True, exist_ok=True)
    train.to_csv(os.path.join(training_output_dir, "train_val.csv"), index=False)

    # Save Testing file (dropping target column), and ground truth labels
    testing_output_dir = "/opt/ml/processing/output/testing"
    pathlib.Path(testing_output_dir).mkdir(parents=True, exist_ok=True)
    test.to_csv(os.path.join(testing_output_dir, "x_test.csv"), index=False, header=False, columns=[name for name in column_names if name != target_attribute])
    test.to_csv(os.path.join(testing_output_dir, "y_test.csv"), header=False, index=False, columns=[target_attribute])
    logger.info("Files successfully created")
    logger.info("Completed running the processing job")