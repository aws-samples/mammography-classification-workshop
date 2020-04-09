import json
import cv2
import boto3
import numpy as np


s3 = boto3.client('s3')


def lambda_handler(event, context):
    bucket = event['bucket']
    key = event['key']

    try:
        s3_object = s3.get_object(Bucket=bucket, Key=key)
        s3_object_byte_array = s3_object['Body'].read()

        # creating 1D array from bytes data range between[0,255]
        np_array = np.fromstring(s3_object_byte_array, np.uint8)

        # decoding array
        s3_object_imdecode = cv2.imdecode(np_array, cv2.IMREAD_UNCHANGED)

        resized_image = cv2.resize(
            s3_object_imdecode, (150, 300), interpolation=cv2.INTER_AREA)

        # saving image to tmp (writable) directory
        tmp_file_name = key.replace("raw/", "resized_")
        print("ResizeMammography.tmp_file_name = "+tmp_file_name)
        cv2.imwrite("/tmp/"+tmp_file_name, resized_image)

        # uploading converted image to S3 bucket
        s3.put_object(Bucket=bucket, Key="resized/"+tmp_file_name,
                      Body=open("/tmp/"+tmp_file_name, "rb").read())

        result = {
            "bucket": bucket,
            "key": "resized/"+tmp_file_name
        }
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }

    except Exception as e:
        print(e)
        raise e
