"""Run a receipt-extraction experiment from code over either dataset.

The task sends each row's image to a vision model and asks for JSON. Code
evaluators compare the extracted fields with the ground-truth columns.

    export ARIZE_API_KEY=...  ARIZE_SPACE_ID=...  OPENAI_API_KEY=...
    python 03_run_experiment.py --dataset receipts-base64
    python 03_run_experiment.py --dataset receipts-urls --model gpt-4.1-mini
"""

import argparse
import json
import os

from arize import ArizeClient
from arize.experiments import EvaluationResult
from openai import OpenAI

PROMPT = (
    "Extract the merchant name, the date (YYYY-MM-DD) and the grand total from this receipt. "
    'Respond with JSON only: {"merchant": string, "date": string, "total": number}'
)

oai = OpenAI()


def make_task(model: str):
    def task(dataset_row) -> str:
        resp = oai.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        # Works for both a data URI and an https URL.
                        {"type": "image_url", "image_url": {"url": dataset_row["image"]}},
                    ],
                }
            ],
        )
        return resp.choices[0].message.content

    return task


def _parse(output) -> dict:
    try:
        return json.loads(output) if isinstance(output, str) else dict(output)
    except (ValueError, TypeError):
        return {}


def total_correct(output, dataset_row) -> EvaluationResult:
    got = _parse(output).get("total")
    expected = float(dataset_row["expected_total"])
    try:
        ok = abs(float(got) - expected) < 0.005
    except (TypeError, ValueError):
        ok = False
    return EvaluationResult(
        score=float(ok),
        label="correct" if ok else "incorrect",
        explanation=f"expected {expected:.2f}, got {got}",
    )


def merchant_correct(output, dataset_row) -> EvaluationResult:
    got = str(_parse(output).get("merchant", ""))
    ok = got.strip().lower() == dataset_row["expected_merchant"].lower()
    return EvaluationResult(
        score=float(ok),
        label="correct" if ok else "incorrect",
        explanation=f"expected {dataset_row['expected_merchant']!r}, got {got!r}",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="receipts-base64")
    parser.add_argument("--model", default="gpt-4.1-mini")
    parser.add_argument("--name", default=None, help="experiment name (default: <model>-from-code)")
    args = parser.parse_args()

    client = ArizeClient(api_key=os.environ["ARIZE_API_KEY"])
    experiment, df = client.experiments.run(
        name=args.name or f"{args.model}-from-code",
        dataset=args.dataset,
        space=os.environ["ARIZE_SPACE_ID"],
        task=make_task(args.model),
        evaluators=[total_correct, merchant_correct],
    )
    print(df.filter(regex="output|eval.*score").to_string())


if __name__ == "__main__":
    main()
