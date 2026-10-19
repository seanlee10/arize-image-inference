# Guide 02: Image inference with URL images

With this approach each dataset row stores an **https link** to the image. The dataset stays small, but the model provider (or Arize) has to be able to download the image when the prompt runs.

## URL requirements

- It must use `https://`. The host must be reachable from the public internet. Private IPs and VPN-only hosts are blocked.
- The **path must end in** `.jpg`, `.jpeg`, `.png`, `.gif` or `.webp`. A query string after the extension is allowed.
  - ✅ `https://cdn.example.com/items/123.jpg`
  - ✅ `https://bucket.s3.amazonaws.com/a/b.png?X-Amz-Signature=...`
  - ❌ `https://cdn.example.com/img/12345` (no extension, so it is sent as text)
  - ❌ `gs://bucket/a.png` or `s3://bucket/a.png` (sent as text, see below)
- The URL must still work **at the time the prompt runs**, not only when you created the dataset.

## Public images

If the images are already public, put the URLs in a column:

```python
import pandas as pd
from arize import ArizeClient

client = ArizeClient(api_key="YOUR_API_KEY")

df = pd.DataFrame({
    "image": [
        "https://cdn.example.com/items/123.jpg",
        "https://cdn.example.com/items/456.png",
    ],
    "expected_label": ["ok", "damaged"],
})

dataset = client.datasets.create(
    name="product-photos-urls",
    space="YOUR_SPACE_ID_OR_NAME",
    examples=df,
)
```

A CSV upload in the UI works the same way.

## Private buckets (GCS / S3)

**Do not store `gs://` or `s3://` URIs in the dataset for inference.** Arize does not sign customer bucket URIs in the playground or experiments, so the model receives the literal text `gs://...`. Choose one of these instead:

- **Presigned https URLs.** These are simple, but they expire. Choose an expiry long enough for every run you plan, and re-sign the URLs for later re-runs.
- **Base64.** Download the images and follow [guide 01](01-base64-images.md). Use this when you need re-runs to keep working.

### GCS: V4 signed URLs

```python
from datetime import timedelta
from google.cloud import storage

gcs = storage.Client()

def sign_gcs(uri: str, hours: int = 24 * 7) -> str:
    bucket, blob = uri.removeprefix("gs://").split("/", 1)
    return gcs.bucket(bucket).blob(blob).generate_signed_url(
        version="v4", expiration=timedelta(hours=hours), method="GET"
    )

df["image"] = df["gcs_uri"].map(sign_gcs)
```

The longest expiry for a V4 signed URL is 7 days.

### S3: presigned URLs

```python
import boto3

s3 = boto3.client("s3")

def sign_s3(uri: str, seconds: int = 7 * 24 * 3600) -> str:
    bucket, key = uri.removeprefix("s3://").split("/", 1)
    return s3.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=seconds
    )

df["image"] = df["s3_uri"].map(sign_s3)
```

Credentials from an STS role or an SSO session cap a presigned URL at that session's lifetime, which can be much shorter than 7 days. Sign with an IAM user or a long-lived role if you need the full 7 days.

Both signers keep the object key, including its `.png`/`.jpg` extension, in the URL path. That means the extension rule above still holds.

## Running it

Running is the same as with base64 ([guide 01](01-base64-images.md), steps 3–4). Load the dataset in the Prompt Playground and put `{{image}}` on its own line in a **user** message.

## Provider notes

- Most providers (OpenAI, Anthropic, Gemini/Vertex, and Bedrock with bearer-token auth) accept https image URLs.
- With **Bedrock using IAM or access-key auth on a Claude model**, https URLs fail with "Please use a base64 data URL instead". Use [guide 01](01-base64-images.md) for that setup.
- With **Azure OpenAI and custom OpenAI-compatible endpoints**, the provider fetches the URL itself. The image host must allow the provider's servers to download it.

## Troubleshooting

| Symptom | Cause |
|---|---|
| The model replies about a URL string instead of describing an image | The URL has no image extension, or it is a `gs://`/`s3://` URI. |
| Provider error "could not download image" or 403 | The presigned URL expired, or the host blocks outside requests. |
| Worked yesterday, fails today | The signed URL expired. Re-sign the URLs, or switch to base64. |
