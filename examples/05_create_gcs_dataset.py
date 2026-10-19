"""Create an Arize dataset from images in a private GCS bucket.

Each row keeps the original gs:// URI for reference and adds a presigned https
URL in the `image` column, which is the one prompts should use. The gs:// URI
itself is NOT an image as far as Arize inference is concerned.

    python -m pip install google-cloud-storage
    export ARIZE_API_KEY=...  ARIZE_SPACE_ID=...
    python 05_create_gcs_dataset.py --bucket my-bucket --prefix receipts/ \
        --signer url-signer@my-project.iam.gserviceaccount.com
"""

import argparse
import csv
import json
import os
from pathlib import Path

from arize import ArizeClient

from sign_urls import SEVEN_DAYS, sign_gcs

HERE = Path(__file__).parent
DATASET_NAME = "receipts-gcs"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", default="receipts/")
    parser.add_argument("--signer", help="service account email to impersonate for signing")
    parser.add_argument("--seconds", type=int, default=SEVEN_DAYS, help="URL lifetime (max 7 days)")
    args = parser.parse_args()

    with open(HERE / "ground_truth.csv") as f:
        truth = list(csv.DictReader(f))

    examples = []
    for row in truth:
        gcs_uri = f"gs://{args.bucket}/{args.prefix}{row['file_name']}"
        url = sign_gcs(gcs_uri, args.seconds, args.signer)
        examples.append(
            {
                "gcs_uri": gcs_uri,  # reference only: sent to the model as plain text
                "image": url,  # presigned https URL: sent to the model as an image
                "image_node": json.dumps({"image.url": url}),  # for evaluators (guide 3)
                "file_name": row["file_name"],
                "expected_merchant": row["merchant"],
                "expected_date": row["date"],
                "expected_total": row["total"],
            }
        )

    client = ArizeClient(api_key=os.environ["ARIZE_API_KEY"])
    dataset = client.datasets.create(
        name=DATASET_NAME,
        space=os.environ["ARIZE_SPACE_ID"],
        examples=examples,
    )
    print(f"Created dataset {DATASET_NAME!r} ({dataset.id}) with {len(examples)} examples")
    print(f"URLs expire in {args.seconds // 3600} hours; re-run this script to re-sign them.")


if __name__ == "__main__":
    main()
