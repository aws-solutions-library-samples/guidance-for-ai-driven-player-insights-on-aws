""" Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. """
""" SPDX-License-Identifier: MIT-0 """

import argparse
import sagemaker

from sagemaker.predictor import Predictor
from sagemaker.serializers import CSVSerializer

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint-name", type=str)
    args, _ = parser.parse_known_args()

    print(F"Using SageMaker Endpoint: {args.endpoint_name}")
    predictor = Predictor(
        endpoint_name=args.endpoint_name,
        sagemaker_session=sagemaker.Session(),
        serializer=CSVSerializer()
    )

    print("Sending inference request with test payload ...")
    response = predictor.predict(
        "bce38d8af2db4373b208a542c86c2f00,2023_01_03,1,casual,726495.490968,6,2,2,29,29,2,2,31,31,0,0,0,0,0,0,0,0,0,0,0,0,1,1,23,23,0,0,0,0,0,0,0,0,1,1,2,2,0,0,0,0,5,5,83,83,1,1,2,2,0,0,0,0,6,6,85,85,0,0,0,0,63786.804794,68952.435853,63905.711339,63966.879159000004,34280.238331,39958.302099,44493.422249,44552.285404,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,64794.13061,71871.599422,68374.651742,68434.265638,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,39438.890551,40453.560301,39915.550449,39986.874358,0.0,0.0,0.0,0.0,17625.643372,23378.615065,78712.996489,78772.872925,39438.890551,40453.560301,39915.550449,39986.874358,0,0,0,0,6861.184569,11824.439271,65602.468347,65662.614135,0,0,0,0,11277.031723999999,8176.905976999999,6619.327086,6623.598556,44661.690301,46810.698517000004,32054.368218,32053.873297000002,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,,,1974.950234,1974.5476879999999,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,,,262.418949,264.275755,0.0,0.0,0.0,0.0,178103.116154,177422.25960999998,175005.372903,175005.805218,,,262.418949,264.275755,0,0,0,0,286395.126206,287668.298387,192654.760168,192654.373818,0,0,0,0"
    ).decode("utf-8")
    print(f"SageMaker returned the following response: {response}")
