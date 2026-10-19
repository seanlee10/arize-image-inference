"""Create an Arize dataset whose `image` column holds https image URLs.

By default the URLs point at the sample receipts hosted on this repo's GitHub
Pages site. Pass --base-url to point at your own host instead.

    export ARIZE_API_KEY=...  ARIZE_SPACE_ID=...
    python 02_create_url_dataset.py
    python 02_create_url_dataset.py --base-url https://cdn.example.com/receipts
"""

import argparse
import csv
import json
import os
from pathlib import Path

from arize import ArizeClient

HERE = Path(__file__).parent
DATASET_NAME = "receipts-urls"
DEFAULT_BASE_URL = "https://seanlee10.github.io/arize-image-inference/examples/images"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()

    with open(HERE / "ground_truth.csv") as f:
        truth = list(csv.DictReader(f))

    examples = []
    for row in truth:
        url = f"{args.base_url.rstrip('/')}/{row['file_name']}"
        examples.append(
            {
                # Playground / experiments: a bare https URL ending in an image extension.
                "image": url,
                # Evaluators: the same URL wrapped as an image content node (see guide 03).
                "image_node": json.dumps({"image.url": url}),
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


if __name__ == "__main__":
    main()
