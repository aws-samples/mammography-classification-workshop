# run with python3
# pip install sklearn
# pip install seaborn

import sys
import boto3
import logging
import json
from sklearn.metrics import confusion_matrix
import seaborn as sn
import pandas as pd
import numpy as np
from botocore.exceptions import ClientError

# bucket = <<'name of the bucket hosting the mammography images'>>

bucket = 'mammography-workshop-files-us-east-2-582783967438'

debug = False
# debug = True

prefix = "resize/validate"

expected = []

predicted = []

def list_bucket_objects(bucket_name, prefix):
    """List the objects in an Amazon S3 bucket

    :param bucket_name: string
    :param prefix: string
    :return: List of bucket objects. If error, return None.
    """

    # Retrieve the list of bucket objects
    s_3 = boto3.client('s3')

    try:
        response = s_3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    except ClientError as e:
        logging.error(e)
        return None

    # Only return the contents if we found some keys
    if response['KeyCount'] > 0:
        return response['Contents']

    return None


def get_object(bucket_name, object_name):
    """Retrieve an object from an Amazon S3 bucket

    :param bucket_name: string
    :param object_name: string
    :return: botocore.response.StreamingBody object. If error, return None.
    """

    # Retrieve the object
    s3 = boto3.client('s3')
    try:
        response = s3.get_object(Bucket=bucket_name, Key=object_name)
    except ClientError as e:
        logging.error(e)
        return None
    # Return an open StreamingBody object
    return response['Body']

def get_expected_value(object_key):
    if "CCD" in object_key:
        return "CC-Right"
    elif "CCE" in object_key:
        return "CC-Left"
    elif "MLOD" in object_key:
        return "MLO-Right"
    elif "MLOE" in object_key:
        return "MLO-Left"
    elif "NAO" in object_key:
        return "Not-a-mammography"
    else:
        logging.warning(object_key)
        sys.exit("Unsupported mammography type on expected array")



def get_classification_of_best_prediction(prediction):

    logging.info(prediction)

    index = np.argmax(prediction)
    object_categories = ['Not-a-mammography', 'CC-Right', 'CC-Left', 'MLO-Right', 'MLO-Left']
    return object_categories[index]


# Set up logging
logger = logging.getLogger()

if debug:
    logger.setLevel(logging.INFO)
else:
    logger.setLevel(logging.WARN)


sagemaker = boto3.client('sagemaker')
sagemaker_runtime = boto3.client('runtime.sagemaker')


endpoints = sagemaker.list_endpoints(SortBy='CreationTime',SortOrder='Descending')

endpoint_name = list(endpoints.values())[0][0]['EndpointName']

# Retrieve the bucket's objects
objects = list_bucket_objects(bucket, prefix)

if objects is not None:
    # List the object names
    logging.info('Objects in ' + bucket)
    for obj in objects:
        object_key = obj["Key"]
        if object_key.endswith(".jpg") or object_key.endswith(".png"):

            logging.info(object_key)

            expected_value = get_expected_value(object_key)

            expected.append(expected_value)

            s3_object = get_object(bucket, object_key)

            s3_object_byte_array = s3_object.read()

            #invoke sagemaker and append on predicted array
            sagemaker_invoke = sagemaker_runtime.invoke_endpoint(EndpointName=endpoint_name,
                                                                 ContentType='application/x-image',
                                                                 Body=s3_object_byte_array)

            prediction = json.loads(sagemaker_invoke['Body'].read().decode())

            best_classification = get_classification_of_best_prediction (prediction)

            if expected_value != best_classification:
                logging.warning(f"Missmatch on {object_key}! Expected: {expected_value} ; Predicted: {best_classification} ")

            predicted.append(best_classification)


else:
    # Didn't get any keys
    logging.warning('No objects in ' + bucket)


#Confusion matrix using scikit learn
results = confusion_matrix(expected, predicted)
print(results)
