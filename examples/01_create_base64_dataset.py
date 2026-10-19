"""Create an Arize dataset whose `image` column holds base64 data URIs.

    export ARIZE_API_KEY=...  ARIZE_SPACE_ID=...
    python 01_create_base64_dataset.py
"""

import base64
import csv
import mimetypes
import os
from pathlib import Path

from arize import ArizeClient

HERE = Path(__file__).parent
DATASET_NAME = "receipts-base64"
ALLOWED = {"image/png", "image/jpeg", "image/gif", "image/webp"}

mimetypes.add_type("image/webp", ".webp")


def to_data_uri(path: Path) -> str:
    """Encode an image file as `data:image/<fmt>;base64,<data>`."""
    mime, _ = mimetypes.guess_type(path.name)
    if mime not in ALLOWED:
        raise ValueError(f"{path.name}: {mime} is not supported (use png/jpeg/gif/webp)")
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def main() -> None:
    with open(HERE / "ground_truth.csv") as f:
        truth = list(csv.DictReader(f))

    examples = [
        {
            "image": to_data_uri(HERE / "images" / row["file_name"]),
            "file_name": row["file_name"],
            "expected_merchant": row["merchant"],
            "expected_date": row["date"],
            "expected_total": row["total"],
        }
        for row in truth
    ]

    client = ArizeClient(api_key=os.environ["ARIZE_API_KEY"])
    dataset = client.datasets.create(
        name=DATASET_NAME,
        space=os.environ["ARIZE_SPACE_ID"],
        examples=examples,
    )
    print(f"Created dataset {DATASET_NAME!r} ({dataset.id}) with {len(examples)} examples")


if __name__ == "__main__":
    main()
