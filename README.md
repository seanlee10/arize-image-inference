# Image Inference in Arize AX

These guides show how to run a vision-capable LLM over images stored in an Arize dataset. You can do it in the **Prompt Playground**, as a saved **experiment**, or with an **LLM-as-judge evaluator** that looks at the image.

Every screenshot and code sample comes from a working run against a real Arize space. The sample data is six synthetic receipts, and the model is asked to extract the merchant, the date and the total from each one. The [`examples/`](https://github.com/seanlee10/arize-image-inference/tree/main/examples) folder contains everything needed to reproduce it.

![Playground running a vision prompt over a dataset of receipt images](assets/screenshots/05-playground-results-base64.png)

## Guides

| # | Guide | What it covers |
|---|---|---|
| 1 | [Base64 images](01-base64-images.md) | Encoding local or private images into the dataset, then running them in the Playground |
| 2 | [URL images](02-url-images.md) | https image links, presigned GCS/S3 URLs, and why `gs://` / `s3://` don't work |
| 3 | [Images in evaluators](03-images-in-evaluators.md) | LLM-as-judge evaluators that look at the image, which need a different column format |
| 4 | [Experiments from code](04-experiments-from-code.md) | Running image experiments from Python, either server-side through an Arize AI integration or locally with your own task |
| 5 | [Troubleshooting](05-troubleshooting.md) | Symptoms, causes and fixes |

## How it works

Arize has no separate "image" field. You store the image as an ordinary string column in the dataset and reference it with a template variable in a **user** message:

```
{image}
Extract the merchant name, the date and the grand total from this receipt.
```

When the prompt runs, Arize checks each variable's value. If the value looks like an image, Arize removes it from the text and sends it to the model as an image instead. Otherwise the value stays as text.

The value counts as an image if it has one of these two forms:

| Form | Example |
|---|---|
| **Base64** | `data:image/png;base64,iVBORw0KGgo...`, or raw base64 with no prefix (Arize identifies the format from the file's first bytes) |
| **https URL** | `https://cdn.example.com/receipts/123.png` or a presigned `https://storage.googleapis.com/...png?X-Goog-Signature=...` |

![Dataset variables recognized as images in the Playground](assets/screenshots/04-playground-setup.png)

## Rules to know before you start

1. **The only formats are JPG/JPEG, PNG, GIF and WebP.** SVG, BMP, TIFF and ICO are rejected on purpose.
2. **`gs://` and `s3://` URIs are sent as text.** The model never sees an image, as shown in [guide 2](02-url-images.md#gs-and-s3-uris-are-not-images). Convert them to presigned https URLs or to base64.
3. **An https URL's path must end in an image extension** (`.png`, `.jpg`, `.jpeg`, `.gif` or `.webp`). A query string after the extension is fine.
4. **Use a vision-capable model.** A text-only model such as `gpt-oss-20b` fails with a provider error ([guide 5](05-troubleshooting.md#text-only-model)).
5. **Put the image variable in a user message, on its own line.**
6. **Evaluators need the image as a JSON node:** `{"image.url": "<url or data URI>"}`. A bare URL stays text ([guide 3](03-images-in-evaluators.md)).

## Base64 or URL?

| | Base64 | https URL |
|---|---|---|
| Private images | ✅ The data is in the row | ⚠️ Needs a presigned URL, which expires |
| Dataset size | Large: about 1.33× the image bytes per row | Small |
| Thumbnails in Arize | ✅ | ✅ |
| Re-run months later | ✅ | Only if the URL still works |

Start with **base64** for private images or up to a few thousand rows. Use **URLs** when the images already sit on a public or CDN host.

## Quick start

```bash
git clone https://github.com/seanlee10/arize-image-inference && cd arize-image-inference/examples
pip install -r requirements.txt
export ARIZE_API_KEY=...  ARIZE_SPACE_ID=...

python make_sample_images.py          # 6 synthetic receipts + ground_truth.csv
python 01_create_base64_dataset.py    # dataset "receipts-base64"
python 02_create_url_dataset.py       # dataset "receipts-urls"
python 03_run_experiment_server_side.py --dataset receipts-urls \
    --integration "<your AI integration name>" --model claude-sonnet-5-5
```
