# Image Inference in Arize AX

These guides cover running a vision-capable LLM over images stored in an Arize dataset, using the Prompt Playground and Experiments.

| Guide | Use it when |
|---|---|
| [01 — Base64 images](01-base64-images.md) | The images are local files or private, and you want each dataset row to carry its own image data. |
| [02 — URL images](02-url-images.md) | The images are already hosted at an https URL (public, or a presigned GCS/S3 link). |
| [03 — Images in evaluators](03-images-in-evaluators.md) | An LLM-as-judge evaluator needs to look at the image. Evaluators use a different input format. |

## How it works

Arize has no separate "image" field. **You store the image as an ordinary string column in the dataset and reference it with a normal template variable** in a **user** message:

```
{{image}}
Describe the product in this photo and list any visible defects.
```

When the playground or an experiment fills in the template, Arize checks each value. If the value looks like an image, Arize removes it from the text and sends it to the model as an image instead. Otherwise the value stays as text.

The value counts as an image if it has one of these two forms:

| Form | Example |
|---|---|
| **Base64** | `data:image/png;base64,iVBORw0KGgo...` (a data URI), or raw base64 with no prefix (Arize identifies the format from the file's first bytes) |
| **https URL** | `https://cdn.example.com/items/123.jpg` or `https://storage.googleapis.com/bucket/x.png?X-Goog-Signature=...` |

Markdown image syntax (`![alt](https://.../x.png)`) also works.

## Rules that trip people up

1. **The only formats are JPG/JPEG, PNG, GIF and WebP.** SVG, BMP, TIFF and ICO are deliberately rejected, because model providers return 400 errors for them. (The public docs page still lists SVG. It is out of date.)
2. **`gs://` and `s3://` URLs do not work for inference.** The playground and experiments treat them as plain text, so the model receives the literal string `gs://...` and never sees an image. Convert them to presigned https URLs ([guide 02](02-url-images.md#private-buckets-gcs--s3)) or to base64 ([guide 01](01-base64-images.md)). The public docs page lists `gs://` and `s3://` as supported. That is wrong for this flow.
3. **An https URL must end in an image extension** (`.jpg`, `.jpeg`, `.png`, `.gif` or `.webp`). A query string after the extension is allowed. A URL with no extension, such as `https://cdn.example.com/img/12345`, is sent as text.
4. **Put the image variable in a user message, separated from other text by whitespace.** Images are only extracted from user messages. In experiments, the image value must also be its own whitespace-separated token. `{{image}}` on its own line is the safest choice.
5. **The model must support vision.** Examples are GPT-4o / 4.1 / 5, Claude Sonnet / Opus / Haiku 4.x, and Gemini.
6. **Bedrock with IAM or access-key auth running a Claude model only accepts base64 PNG or JPEG.** It rejects https URLs with "Invalid image URL format for Anthropic model. Please use a base64 data URL instead". Use [guide 01](01-base64-images.md) for that setup.
7. **Raw base64 is limited to about 10 MB of text** (roughly 7.5 MB of image). Model providers have their own lower limits. For example, Anthropic allows about 5 MB per image. Resize large images first.

## Choosing between base64 and a URL

| | Base64 | https URL |
|---|---|---|
| Works with private images | ✅ The data is in the row | ⚠️ Needs a presigned URL, which expires |
| Dataset size | Large: about 1.33× the image bytes per row | Small |
| Thumbnails in the dataset table | ✅ | ✅ |
| Bedrock Claude with IAM auth | ✅ PNG and JPEG only | ❌ |
| Re-run the experiment months later | ✅ | Only if the URL still works |

Start with **base64** if the images are private or there are fewer than a few thousand of them. Use **https URLs** if the images are already on a public or CDN host.
