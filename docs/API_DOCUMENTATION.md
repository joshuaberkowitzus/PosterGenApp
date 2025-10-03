# PosterGen API Documentation

## Overview

The PosterGen API provides an automated service for generating professional academic posters from research papers. The API uses a multi-agent AI system that analyzes PDF papers and creates visually appealing, well-structured posters in PowerPoint format.

## Base URL

```
http://localhost:8080  # Local development
https://[your-cloud-run-url]  # Production (Cloud Run)
```

## Authentication

Currently, the API does not require authentication for requests. However, it requires proper Google Cloud Platform (GCP) credentials for accessing Google Cloud Storage (GCS) buckets and Secret Manager.

---

## Endpoints

### POST `/generate-poster/`

Generates an academic poster from a PDF paper stored in Google Cloud Storage.

#### Request

**Content-Type:** `application/json`

**Request Body Structure:**

```json
{
  "gcs_input_bucket": "string (required)",
  "gcs_output_bucket": "string (required)",
  "pdf_path": "string (required)",
  "logo": "string (optional)",
  "aff_logo": "string (optional)",
  "text_model": "string (optional)",
  "multimodal_model": "string (optional)",
  "image_model": "string (optional)",
  "fast_llm_model": "string (optional)",
  "fast_search": "boolean (optional)",
  "output_path": "string (optional)",
  "debug_mode": "boolean (optional)",
  "width": "integer (optional)",
  "height": "integer (optional)",
  "url": "string (optional)"
}
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `gcs_input_bucket` | string | **Yes** | - | Name of the GCS bucket containing input files (paper PDF and logos) |
| `gcs_output_bucket` | string | **Yes** | - | Name of the GCS bucket where the generated poster will be uploaded |
| `pdf_path` | string | **Yes** | - | Path to the PDF paper within the input bucket (e.g., `papers/my-paper.pdf`) |
| `logo` | string | No | `null` | Path to conference/journal logo within the input bucket (e.g., `logos/conference.png`) |
| `aff_logo` | string | No | `null` | Path to affiliation/institution logo within the input bucket (e.g., `logos/university.png`) |
| `text_model` | string | No | `"gpt-5-2025-08-07"` | AI model for text processing and content generation |
| `multimodal_model` | string | No | `"gpt-5-2025-08-07"` | AI model for multimodal analysis (text + images) |
| `image_model` | string | No | `"gpt-image-1"` | AI model for image generation |
| `fast_llm_model` | string | No | `"gpt-5-mini-2025-08-07"` | Faster AI model for less critical tasks |
| `fast_search` | boolean | No | `false` | Enable faster processing with reduced accuracy |
| `output_path` | string | No | `"poster.pptx"` | Name of the output poster file |
| `debug_mode` | boolean | No | `false` | Enable debug mode for verbose logging |
| `width` | integer | No | `42` | Poster width in inches |
| `height` | integer | No | `28` | Poster height in inches |
| `url` | string | No | `null` | URL to encode as QR code on the poster (e.g., paper URL, project website) |

#### Parameter Formats

- **Bucket names:** Standard GCS bucket naming (e.g., `my-poster-bucket`)
- **File paths:** Relative paths within buckets, including file extension (e.g., `papers/2024/my-paper.pdf`)
- **Logo formats:** PNG, JPG, or other common image formats
- **Dimensions:** 
  - Poster width and height are in inches
  - Recommended aspect ratio: between 1.4 (ISO A paper) and 2.0 (human vision limit)
  - Common sizes: 42×28 (3:2), 48×32 (3:2), 54×36 (3:2)
- **URLs:** Full URLs including protocol (e.g., `https://example.com/paper`)

#### Example Request

```bash
curl -X POST "http://localhost:8080/generate-poster/" \
  -H "Content-Type: application/json" \
  -d '{
    "gcs_input_bucket": "my-research-papers",
    "gcs_output_bucket": "generated-posters",
    "pdf_path": "papers/2024/quantum-computing.pdf",
    "logo": "logos/conference-logo.png",
    "aff_logo": "logos/university-logo.png",
    "text_model": "gpt-5-2025-08-07",
    "width": 48,
    "height": 32,
    "url": "https://example.com/quantum-paper"
  }'
```

#### Python Example

```python
import requests

url = "http://localhost:8080/generate-poster/"
payload = {
    "gcs_input_bucket": "my-research-papers",
    "gcs_output_bucket": "generated-posters",
    "pdf_path": "papers/2024/quantum-computing.pdf",
    "logo": "logos/conference-logo.png",
    "aff_logo": "logos/university-logo.png",
    "text_model": "gpt-5-2025-08-07",
    "width": 48,
    "height": 32,
    "url": "https://example.com/quantum-paper"
}

response = requests.post(url, json=payload)
print(response.json())
```

#### Response

**Success Response (200 OK):**

```json
{
  "status": "success",
  "output_path": "gs://generated-posters/quantum-computing.pptx"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Operation status (`"success"` or `"error"`) |
| `output_path` | string | Full GCS path to the generated poster file |

**Error Response (500 Internal Server Error):**

```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Workflow Pipeline

The poster generation process follows a multi-agent workflow:

1. **Parser Agent** - Extracts content from the PDF paper
2. **Curator Agent** - Creates a storyboard and organizes content
3. **Color Agent** - Designs the color scheme
4. **Section Title Designer** - Styles section titles and headers
5. **Layout Optimizer** - Optimizes content layout and balance
6. **Font Agent** - Selects and applies appropriate typography
7. **Renderer** - Generates the final PowerPoint file

### Processing Time

⚠️ **Important:** This is a **long-running operation** (typically 5-15 minutes depending on paper complexity and model choices). The API currently blocks until completion.

**TODO:** Status streaming will be added in a future update to provide real-time progress updates.

---

## Error Handling

### Common Errors

| Status Code | Error | Cause | Solution |
|-------------|-------|-------|----------|
| 500 | `"Generated poster file not found"` | Workflow completed but output file missing | Check workflow logs, verify write permissions |
| 500 | `"Workflow final state did not contain output_dir or poster_name"` | Workflow failed to complete properly | Check agent logs for failures |
| 500 | General exceptions | Various (GCS access, API keys, etc.) | Check error detail in response |

### Prerequisites for Success

1. **GCS Access:** Service account must have read access to input bucket and write access to output bucket
2. **API Keys:** Required API keys must be available in GCP Secret Manager or environment variables:
   - `OPENAI_API_KEY` (for GPT models)
   - `ANTHROPIC_API_KEY` (for Claude models)
   - `GOOGLE_API_KEY` (for Gemini models)
   - `ZHIPU_API_KEY` (for GLM models)
3. **Valid PDF:** Input PDF must be a readable academic paper
4. **Valid Logos:** If provided, logo files must be valid image files

---

## Model Options

### Text Models

- `gpt-4o-2024-08-06` (previous default)
- `gpt-5-2025-08-07` (current default) ⭐
- `gpt-4.1-2025-04-14`
- `gpt-4.1-mini-2025-04-14`
- `claude-sonnet-4-20250514`
- `gemini-2.5-pro`
- `glm-4.5`
- `glm-4.5-air`
- `glm-4`

### Vision/Multimodal Models

- `gpt-4o-2024-08-06`
- `gpt-5-2025-08-07` (current default) ⭐
- `gpt-4.1-2025-04-14`
- `gpt-4.1-mini-2025-04-14`
- `claude-sonnet-4-20250514`
- `gemini-2.5-pro`
- `glm-4.5v`
- `glm-4v`

### Image Generation Models

- `gpt-image-1` (current default) ⭐
- `dall-e-3` (previous default)

### Fast Models

- `gpt-5-mini-2025-08-07` (current default) ⭐

---

## Deployment

### Local Development

```bash
# Set environment variables
export PORT=8080
export GCP_PROJECT_ID=your-project-id

# Run with uvicorn
uvicorn src.workflow.pipeline:app --host 0.0.0.0 --port 8080
```

### Cloud Run Deployment

The application is designed to run on Google Cloud Run. The `PORT` environment variable is automatically provided by Cloud Run.

```bash
# Deploy to Cloud Run
gcloud run deploy postgen-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

---

## Limitations & Known Issues

1. **Long Processing Time:** Poster generation takes 5-15 minutes with no progress updates
   - **TODO:** Add status streaming/webhooks for progress updates
2. **Synchronous Operation:** API blocks until completion (no job queue)
3. **No Authentication:** Currently open access (add authentication before production use)
4. **GCS Only:** Only supports Google Cloud Storage (no local file system or other cloud providers)
5. **Single Request:** No batch processing capability

---

## Future Enhancements

- [ ] Add WebSocket or Server-Sent Events for real-time status updates
- [ ] Implement job queue for asynchronous processing
- [ ] Add authentication and API key management
- [ ] Support for direct file uploads (without GCS)
- [ ] Batch processing endpoint
- [ ] Poster preview endpoint (low-res preview before full generation)
- [ ] Template selection options
- [ ] Custom color scheme specification
- [ ] Progress callbacks via webhooks

---

## Support

For issues, questions, or feature requests, please refer to the project repository.

## License

[Specify your license here]
