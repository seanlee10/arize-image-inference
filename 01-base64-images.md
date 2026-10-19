# Guide 01: Image inference with base64 images

With this approach each dataset row contains the image itself. You don't need to host the images or manage URL expiry, and it works with every vision provider.

## 1. Encode the images

Store each image as a **data URI**: `data:image/<fmt>;base64,<data>`. Raw base64 with no prefix also works, but the data URI states the format explicitly and removes any doubt.

```python
import base64
import mimetypes
from pathlib import Path

ALLOWED = {"image/png", "image/jpeg", "image/gif", "image/webp"}

def to_data_uri(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    if mime not in ALLOWED:
        raise ValueError(f"{path}: {mime} is not supported (use png/jpeg/gif/webp)")
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"
```

Optionally, shrink large images before encoding. This makes the dataset smaller and keeps you under provider limits:

```python
from io import BytesIO
from PIL import Image

def to_data_uri_resized(path: Path, max_side: int = 1568) -> str:
    img = Image.open(path).convert("RGB")
    img.thumbnail((max_side, max_side))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
```

## 2. Create the dataset

### Using the Python SDK (v8)

```python
import pandas as pd
from arize import ArizeClient

client = ArizeClient(api_key="YOUR_API_KEY")

image_dir = Path("./images")
rows = [
    {
        "image": to_data_uri(p),
        "file_name": p.name,
        "expected_label": "...",  # optional ground truth for evals
    }
    for p in sorted(image_dir.glob("*"))
    if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}
]

dataset = client.datasets.create(
    name="product-photos-base64",
    space="YOUR_SPACE_ID_OR_NAME",
    examples=pd.DataFrame(rows),
)
print(dataset.id)
```

### Using a CSV upload in the UI

Write the same DataFrame out with `df.to_csv("images.csv", index=False)`, then go to **Datasets → New Dataset → Upload CSV**. Base64 makes CSVs large very quickly, so for more than a few hundred images use the SDK instead. The SDK streams large uploads.

Once the dataset is created, the `image` column shows thumbnails in the dataset table. That confirms Arize recognized the values as images.

## 3. Run it in the Prompt Playground

1. Open **Prompt Playground** and choose a vision-capable model.
2. Load the dataset with **Dataset → `product-photos-base64`**.
3. Write the **user** message with the image variable on its own line:

   ```
   {{image}}
   Classify this product photo as one of: ok, damaged, wrong_item.
   Respond with only the label.
   ```

   If the template uses f-string format, write `{image}` instead.
4. Click **Run**. Each row's image is sent to the model as an image, and the `{{image}}` text is removed from the prompt.

## 4. Run it as an experiment

Choose **Run on dataset** in the playground to save the run as an experiment, so you can compare models or prompts side by side.

Alternatively, run it from code. The task function receives the dataset row, so you build the multimodal message yourself:

```python
from openai import OpenAI

oai = OpenAI()

def task(dataset_row) -> str:
    resp = oai.chat.completions.create(
        model="gpt-4.1",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "Classify this product photo as ok, damaged, or wrong_item."},
                {"type": "image_url", "image_url": {"url": dataset_row["image"]}},
            ],
        }],
    )
    return resp.choices[0].message.content

client.experiments.run(
    name="gpt-4.1-classifier",
    dataset=dataset.id,
    task=task,
)
```

## Troubleshooting

| Symptom | Cause |
|---|---|
| The model answers "I don't see an image", or its reply quotes base64 text | The value wasn't recognized as an image. Check the MIME type (png/jpeg/gif/webp only), and check that the string has no stray quotes or newlines inside it. |
| No thumbnail in the dataset table | Same cause as above: Arize doesn't recognize the value as an image. |
| Provider 400 error saying the image is too large | Resize the image. Anthropic's limit is about 5 MB per image, and raw base64 over about 10 MB of text is ignored. |
| The image is ignored when it is in a system message | Images are only taken from **user** messages. |
