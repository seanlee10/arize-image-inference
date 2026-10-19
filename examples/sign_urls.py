"""Turn gs:// and s3:// URIs into presigned https URLs Arize can use.

Arize does not sign customer bucket URIs during playground or experiment
inference, so convert them before creating the dataset.

    pip install google-cloud-storage boto3
    python sign_urls.py gs://my-bucket/receipts/receipt_01.png s3://my-bucket/receipts/receipt_02.jpg
"""

import sys
from datetime import timedelta

SEVEN_DAYS = 7 * 24 * 3600  # the maximum for both GCS V4 and S3 SigV4


def sign_gcs(uri: str, seconds: int = SEVEN_DAYS) -> str:
    from google.cloud import storage

    bucket, blob = uri.removeprefix("gs://").split("/", 1)
    return (
        storage.Client()
        .bucket(bucket)
        .blob(blob)
        .generate_signed_url(version="v4", expiration=timedelta(seconds=seconds), method="GET")
    )


def sign_s3(uri: str, seconds: int = SEVEN_DAYS) -> str:
    import boto3

    bucket, key = uri.removeprefix("s3://").split("/", 1)
    return boto3.client("s3").generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=seconds
    )


def sign(uri: str, seconds: int = SEVEN_DAYS) -> str:
    if uri.startswith("gs://"):
        return sign_gcs(uri, seconds)
    if uri.startswith("s3://"):
        return sign_s3(uri, seconds)
    return uri


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        print(sign(arg))
