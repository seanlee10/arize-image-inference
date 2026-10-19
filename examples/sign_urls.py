"""Turn gs:// and s3:// URIs into presigned https URLs Arize can use.

Arize does not sign customer bucket URIs during playground or experiment
inference, so convert them before creating the dataset.

GCS V4 signing needs a service account. With user credentials (`gcloud auth
application-default login`), pass --signer to sign by impersonating a service
account; you need roles/iam.serviceAccountTokenCreator on it, and the service
account needs read access to the bucket.

    pip install google-cloud-storage boto3
    python sign_urls.py --signer url-signer@my-project.iam.gserviceaccount.com gs://my-bucket/receipts/receipt_01.png
    python sign_urls.py s3://my-bucket/receipts/receipt_02.jpg
"""

import argparse
from datetime import timedelta

SEVEN_DAYS = 7 * 24 * 3600  # the maximum for both GCS V4 and S3 SigV4


def sign_gcs(uri: str, seconds: int = SEVEN_DAYS, signer: str | None = None) -> str:
    import google.auth
    from google.auth import impersonated_credentials
    from google.cloud import storage

    credentials = None
    if signer:
        source, _ = google.auth.default()
        credentials = impersonated_credentials.Credentials(
            source_credentials=source,
            target_principal=signer,
            target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
    bucket, blob = uri.removeprefix("gs://").split("/", 1)
    return (
        storage.Client(credentials=credentials)
        .bucket(bucket)
        .blob(blob)
        .generate_signed_url(
            version="v4", expiration=timedelta(seconds=seconds), method="GET", credentials=credentials
        )
    )


def sign_s3(uri: str, seconds: int = SEVEN_DAYS) -> str:
    import boto3

    bucket, key = uri.removeprefix("s3://").split("/", 1)
    return boto3.client("s3").generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=seconds
    )


def sign(uri: str, seconds: int = SEVEN_DAYS, signer: str | None = None) -> str:
    if uri.startswith("gs://"):
        return sign_gcs(uri, seconds, signer)
    if uri.startswith("s3://"):
        return sign_s3(uri, seconds)
    return uri


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("uris", nargs="+")
    parser.add_argument("--signer", help="service account email to impersonate for GCS signing")
    parser.add_argument("--seconds", type=int, default=SEVEN_DAYS)
    args = parser.parse_args()
    for uri in args.uris:
        print(sign(uri, args.seconds, args.signer))
