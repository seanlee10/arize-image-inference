"""Run the receipt prompt over a dataset on Arize's servers, from code.

Arize makes the LLM calls through an AI integration configured in your space,
so no provider API key is needed locally. This uses the same pipeline as the
Playground's "Run" on a dataset: `{{image}}` is filled from the dataset row and
the value is sent to the model as an image.

    export ARIZE_API_KEY=...  ARIZE_SPACE_ID=...
    python 03_run_experiment_server_side.py --dataset receipts-urls \
        --integration "Anthropic 1" --model claude-sonnet-5-5
"""

import argparse
import os
import time

from arize import ArizeClient

from scoring import date_correct, merchant_correct, total_correct

PROMPT = (
    "{{image}}\n"
    "Extract the merchant name, the date and the grand total from this receipt. "
    "Respond with JSON only, using the keys merchant, date (YYYY-MM-DD) and total (a number)."
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="receipts-urls")
    parser.add_argument("--integration", default="Anthropic 1", help="AI integration name in Arize")
    parser.add_argument("--model", default="claude-sonnet-5-5")
    args = parser.parse_args()

    space = os.environ["ARIZE_SPACE_ID"]
    client = ArizeClient(api_key=os.environ["ARIZE_API_KEY"])

    integration = client.ai_integrations.list(space=space, name=args.integration).ai_integrations[0]

    task = client.tasks.create_run_experiment_task(
        name=f"{args.dataset}-{args.model}-{int(time.time())}",
        dataset=args.dataset,
        space=space,
        run_configuration={
            "experiment_type": "LLM_GENERATION",
            "ai_integration_id": integration.id,
            "model_name": args.model,
            "input_variable_format": "MUSTACHE",  # {{image}}; use F_STRING for {image}
            "messages": [{"role": "USER", "content": PROMPT}],
        },
    )
    run = client.tasks.trigger_run(task=task.id, experiment_name=f"{args.model} (server-side)")
    run = client.tasks.wait_for_run(run_id=run.id)
    print(f"Run {run.status}: {run.num_successes} succeeded, {run.num_errors} failed")

    # Score the outputs locally against the ground-truth columns.
    examples = {
        e.id: e.additional_properties
        for e in client.datasets.list_examples(dataset=args.dataset, space=space, all=True).examples
    }
    runs = client.experiments.list_runs(experiment=run.experiment_id, limit=100).experiment_runs
    checks = {"total": total_correct, "merchant": merchant_correct, "date": date_correct}
    for name, check in checks.items():
        hits = sum(check(r.output, examples[r.example_id]) for r in runs)
        print(f"{name:>8} correct: {hits}/{len(runs)}")


if __name__ == "__main__":
    main()
