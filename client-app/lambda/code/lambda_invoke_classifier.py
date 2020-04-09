import json
import boto3
import os


s3 = boto3.client('s3')
sagemaker = boto3.client('runtime.sagemaker')
lambda_client = boto3.client('lambda')

NAO = 0
CCD = 1
CCE = 2
MLOD = 3
MLOE = 4


def get_description(best_prediction_position, prediction):

    chance = f'{prediction[best_prediction_position]*100:.2f}'

    if(best_prediction_position == NAO):
        return "Chance of " + chance + "% of not being mammography"
    elif(best_prediction_position == CCD):
        return "Chance of " + chance + "% of being a Cranial-Caudal Right (CC-Right)"
    elif(best_prediction_position == CCE):
        return "Chance of " + chance + "% of being a Cranial-Caudal Left (CC-Left)"
    elif(best_prediction_position == MLOD):
        return "Chance of " + chance + "% of being a Mediolateral-Oblique Right (MLO-Right)"
    elif(best_prediction_position == MLOE):
        return "Chance of " + chance + "% of being a Mediolateral-Oblique Left (MLO-Left)"


def get_object(bucket_name, object_name):
    """Retrieve an object from an Amazon S3 bucket

    :param bucket_name: string
    :param object_name: string
    :return: botocore.response.StreamingBody object. If error, return None.
    """

    # Retrieve the object
    try:
        response = s3.get_object(Bucket=bucket_name, Key=object_name)
    except ClientError as e:
        # AllAccessDisabled error == bucket or object not found
        return None
    # Return an open StreamingBody object
    return response['Body']


def get_best_prediction_position(prediction):

    higher_prediction = prediction[NAO]
    position_higher_prediction = NAO

    if prediction[CCD] > higher_prediction:
        higher_prediction = prediction[CCD]
        position_higher_prediction = CCD
    if prediction[CCE] > higher_prediction:
        higher_prediction = prediction[CCE]
        position_higher_prediction = CCE
    if prediction[MLOD] > higher_prediction:
        higher_prediction = prediction[MLOD]
        position_higher_prediction = MLOD
    if prediction[MLOE] > higher_prediction:
        higher_prediction = prediction[MLOE]
        position_higher_prediction = MLOE

    return position_higher_prediction


def lambda_handler(event, context):
    # Get the object from the event and show its content type
    bucket = event['bucket']
    key = event['key']

    try:
        payload = {
            "bucket": bucket,
            "key": key
        }

        resized_location_lambda = lambda_client.invoke(
            FunctionName="ResizeMammography",
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        resized_location = json.load(resized_location_lambda['Payload'])

        body = json.loads(resized_location['body'])
        resized_bucket = body['bucket']
        resized_key = body['key']

        s3_object = get_object(resized_bucket, resized_key)

        s3_object_byte_array = s3_object.read()

        # invoke sagemaker and append on predicted array
        sagemaker_invoke = sagemaker.invoke_endpoint(EndpointName=os.environ['endpoint_name'],
                                                     ContentType='application/x-image',
                                                     Body=s3_object_byte_array)

        prediction = json.loads(sagemaker_invoke['Body'].read().decode())
        best_prediction_position = get_best_prediction_position(prediction)

        return get_description(best_prediction_position, prediction)

    except Exception as e:
        print(e)
        raise e
