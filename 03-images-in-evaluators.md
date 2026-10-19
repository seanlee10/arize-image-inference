# Guide 03: Images in LLM-as-judge evaluators

Evaluators recognize images differently from the playground and experiments.

| | Playground / experiment task | Evaluator |
|---|---|---|
| How an image is recognized | **By its value.** Any bare image URL or base64 string becomes an image. | **By structure.** The value must be a JSON object with an `image.url` key. |
| A bare `https://...png` string | Sent as an image | Stays **text** |

Evaluators work this way on purpose. Many evals legitimately classify URLs as text (for example, "is this link phishing?"), so an evaluator only switches to vision when the data explicitly marks something as an image.

## Making a dataset column usable as an evaluator image

Store the column (or map the evaluator variable to a value) as an image content node:

```json
{"image.url": "data:image/png;base64,iVBORw0KGgo..."}
```

The nested form also works:

```json
{"image": {"url": "https://cdn.example.com/items/123.jpg"}}
```

The same format rules as the other guides apply: png/jpeg/gif/webp only, and https URLs must end in an image extension.

```python
df["image_node"] = df["image"].map(lambda v: {"image.url": v})
```

> ⚠️ It is not yet confirmed how the experiment runner turns a dict cell into a string before the evaluator sees it. Before relying on this in a large run, test it on a 2–3 row dataset and check that the judge's explanation describes the image.

## Evaluating traced spans (online evals)

If your app is instrumented with OpenInference, image message parts on spans already look like `message_content.image` → `image.url`. In the evaluator's column mapping, map your template variable (for example `{img}`) to the span's **`...image`** column, not to `...image.image.url`.

Images that your app sent inline as base64 are moved by Arize into its own storage when the spans arrive. Evaluators can still read them: Arize signs those internal `gs://` links automatically, scoped to your project. This is the **only** case where a `gs://`/`s3://` URL works, and it applies only to images Arize itself stored. It never applies to your own buckets.

## Requirements

- The judge model must support image input. Otherwise the UI shows "This template uses image variables but the selected model does not support image input".
- If you only need to score the model's **text output** (for example, comparing it to `expected_label`), you don't need images in the evaluator at all. Use a plain text or code evaluator.
