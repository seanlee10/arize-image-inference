"""Run the receipt task locally with your own Anthropic key, scored by code evaluators.

Use this when the task is more than a single prompt (pre-processing, tools,
multiple calls). The SDK downloads the dataset, runs `task` for every row,
scores the output with the evaluators and uploads everything as an experiment.

    pip install anthropic
    export ARIZE_API_KEY=...  ARIZE_SPACE_ID=...  ANTHROPIC_API_KEY=...
    python 04_run_experiment_local.py --dataset receipts-base64
"""

import argparse
import os
import re

import anthropic
from arize import ArizeClient
from arize.experiments import EvaluationResult

from scoring import date_correct, merchant_correct, parse_output, total_correct

PROMPT = (
    "Extract the merchant name, the date and the grand total from this receipt. "
    "Respond with JSON only, using the keys merchant, date (YYYY-MM-DD) and total (a number)."
)
DATA_URI = re.compile(r"^data:(image/[a-z]+);base64,(.*)$", re.DOTALL)

claude = anthropic.Anthropic()


def image_block(value: str) -> dict:
    """Build an Anthropic image block from a data URI or an https URL."""
    if m := DATA_URI.match(value):
        return {"type": "image", "source": {"type": "base64", "media_type": m[1], "data": m[2]}}
    return {"type": "image", "source": {"type": "url", "url": value}}


def make_task(model: str):
    def task(dataset_row) -> str:
        msg = claude.messages.create(
            model=model,
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": [image_block(dataset_row["image"]), {"type": "text", "text": PROMPT}],
                }
            ],
        )
        return msg.content[0].text

    return task


def _result(ok: bool, field: str, output, dataset_row) -> EvaluationResult:
    return EvaluationResult(
        score=float(ok),
        label="correct" if ok else "incorrect",
        explanation=f"expected {dataset_row[f'expected_{field}']}, got {parse_output(output).get(field)}",
    )


# Evaluators receive arguments by parameter name: output, dataset_row, input, metadata, ...
def total_evaluator(output, dataset_row) -> EvaluationResult:
    return _result(total_correct(output, dataset_row), "total", output, dataset_row)


def merchant_evaluator(output, dataset_row) -> EvaluationResult:
    return _result(merchant_correct(output, dataset_row), "merchant", output, dataset_row)


def date_evaluator(output, dataset_row) -> EvaluationResult:
    return _result(date_correct(output, dataset_row), "date", output, dataset_row)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="receipts-base64")
    parser.add_argument("--model", default="claude-sonnet-5-5")
    parser.add_argument("--dry-run", action="store_true", help="run 3 rows locally without uploading")
    args = parser.parse_args()

    client = ArizeClient(api_key=os.environ["ARIZE_API_KEY"])
    experiment, df = client.experiments.run(
        name=f"{args.model} (local task)",
        dataset=args.dataset,
        space=os.environ["ARIZE_SPACE_ID"],
        task=make_task(args.model),
        evaluators=[total_evaluator, merchant_evaluator, date_evaluator],
        dry_run=args.dry_run,
        dry_run_count=3,
    )
    print(df.filter(regex=r"^output$|eval\..*\.score").to_string())


if __name__ == "__main__":
    main()
