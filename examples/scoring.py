"""Compare a model's receipt JSON with the ground-truth columns."""

import json
import re

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def parse_output(output) -> dict:
    """Parse model output as JSON, tolerating ```json fences around it."""
    if isinstance(output, dict):
        return output
    try:
        return json.loads(_FENCE.sub("", str(output).strip()))
    except (TypeError, ValueError):
        return {}


def total_correct(output, dataset_row) -> bool:
    got = parse_output(output).get("total")
    try:
        return abs(float(got) - float(dataset_row["expected_total"])) < 0.005
    except (TypeError, ValueError):
        return False


def merchant_correct(output, dataset_row) -> bool:
    got = str(parse_output(output).get("merchant", ""))
    return got.strip().lower() == str(dataset_row["expected_merchant"]).lower()


def date_correct(output, dataset_row) -> bool:
    return str(parse_output(output).get("date", "")) == str(dataset_row["expected_date"])
