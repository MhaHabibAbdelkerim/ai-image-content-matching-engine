# Build Log — AI Image Content Matching Engine

## Project Overview

This project is an AI-powered backend system that analyzes images, generates structured metadata and embeddings, and matches images to blog posts using semantic similarity and rule-based mismatch protection.

The system was developed as a backend engineering capstone with a focus on:

* Reliable API design
* Structured AI output
* PostgreSQL persistence
* Background processing
* Retry handling
* Semantic image matching
* Mismatch detection
* Human review
* AI usage and cost tracking
* Automated evaluation
* Automated testing
* Docker-based deployment

---

## Stage 1 — Project and FastAPI Setup

### Goal

Create the initial backend structure and establish a clean layered architecture.

### Implementation

Created a FastAPI application with separate areas for:

```text
app/
├── main.py
├── api/
│   └── routes/
├── services/
├── models/
├── schemas/
├── db/
├── workers/
└── core/
```

Configured a Python virtual environment and installed the initial FastAPI and Uvicorn dependencies.

Added a root endpoint:

```text
GET /
```

### Result

The application could start successfully and provide a basic API foundation for the remaining stages.

---

## Stage 2 — PostgreSQL Database and Migrations

### Goal

Introduce persistent storage and database migrations.

### Implementation

Added PostgreSQL using Docker Compose and the `pgvector/pgvector:pg17` image.

The API connects to PostgreSQL through SQLAlchemy and psycopg.

Created the database layer with:

* SQLAlchemy declarative base
* Database engine
* Session factory
* FastAPI database dependency

Added Alembic for schema migrations.

The database includes support for vector embeddings through pgvector.

### Important Engineering Decision

The PostgreSQL container uses host port `5433` because another local PostgreSQL container was already using port `5432`.

The API container communicates with PostgreSQL internally using:

```text
postgresql+psycopg://postgres:postgres@db:5432/image_matching
```

### Result

The application gained persistent database storage and version-controlled database schema changes.

---

## Stage 3 — Image Ingestion API

### Goal

Allow images to be submitted to the system and processed asynchronously.

### Implementation

Added:

```text
POST /images/
GET /images/{image_id}
GET /images/jobs/{job_id}
```

Image submission creates:

1. An image record.
2. An image-processing job.
3. An idempotency record.

The API uses Pydantic validation for incoming image URLs.

### Result

Images can be submitted through the API and associated with processing jobs that track their status.

---

## Stage 4 — Vision AI Pipeline

### Goal

Extract structured information from images using a vision model.

### Implementation

The original implementation explored Gemini, but API access/key restrictions prevented reliable use in the local development environment.

The project was therefore adapted to use local Ollama with:

```text
llava:latest
```

The vision model is instructed to return structured JSON containing:

```text
subject
category
attributes
caption
confidence
```

The output is validated using a Pydantic schema.

### Validation

The `confidence` field is constrained to:

```text
0.0 <= confidence <= 1.0
```

The system also instructs the vision model to identify specific subjects rather than generic labels.

For example, animals should be identified as specifically as possible:

```text
fox
wolf
lion
dog
cat
```

### Result

The system can convert an image into validated structured metadata.

---

## Stage 5 — Background Processing and Retries

### Goal

Move image processing into a background workflow and handle temporary failures safely.

### Implementation

Added image-processing workers that:

1. Retrieve the image.
2. Run vision analysis.
3. Store structured metadata.
4. Generate an embedding.
5. Update the processing job.
6. Record errors when processing fails.

The worker supports up to three attempts.

Retryable failures include:

* Connection errors
* Timeouts
* HTTP 429 responses
* HTTP 5xx responses

Permanent errors such as HTTP 404 responses are not retried.

Retry delays use exponential backoff with jitter.

### Example

The retry delay is based on:

```text
base delay × 2^(attempt - 1)
```

with a maximum delay cap and a small random jitter.

### Result

Temporary infrastructure failures can be retried while permanent failures do not waste additional attempts.

---

## Stage 6 — Semantic Embeddings

### Goal

Represent image metadata as vectors so images can be matched semantically against blog posts.

### Implementation

Added Ollama embeddings using:

```text
nomic-embed-text
```

The embedding model produces 768-dimensional vectors.

Image metadata is combined into text such as:

```text
Subject: fox.
Category: animal.
Attributes: ...
Caption: ...
```

This text is converted into an embedding and stored in PostgreSQL using pgvector.

### Result

Images can be compared using vector similarity rather than only exact keyword matching.

---

## Stage 7 — Semantic Image Matching

### Goal

Find images that are semantically relevant to a blog post.

### Implementation

Blog posts were added with:

```text
title
content
subject
embedding
```

Blog post text is embedded and compared with stored image embeddings.

The system uses cosine distance through pgvector and converts the distance into a similarity score:

```text
similarity = 1 - cosine_distance
```

Images are ordered by similarity to identify the strongest candidates.

### Result

A blog post can retrieve semantically similar images from the database.

---

## Stage 8 — Mismatch Guard

### Goal

Prevent semantically similar but incorrect images from being accepted.

A major example is preventing a wolf image from being recommended for a fox article simply because their embeddings are semantically similar.

### Implementation

The mismatch guard evaluates:

1. Similarity threshold
2. Image confidence
3. Expected subject
4. Actual image subject

Default thresholds are:

```text
MATCH_SIMILARITY_THRESHOLD = 0.70
MIN_IMAGE_CONFIDENCE = 0.70
```

A candidate is rejected if:

* Similarity is too low.
* Confidence is missing.
* Confidence is below the configured threshold.
* The image subject does not match the expected subject.

The guard returns a human-readable explanation for every rejection.

### Example

A wolf image tested against a fox article produced a high semantic similarity but was rejected because:

```text
Image subject "wolf" does not match expected subject "fox".
```

### Result

The matching system combines semantic retrieval with explicit subject-level safety checks.

---

## Stage 9 — Human Review API

### Goal

Allow uncertain image metadata to be reviewed by a human.

### Implementation

Added review fields to images:

```text
needs_review
review_status
review_reason
reviewed_at
```

Added:

```text
POST /images/{image_id}/review
GET /images/{image_id}/review
GET /images/review/pending
```

Review decisions are restricted to:

```text
approved
rejected
```

using Pydantic validation.

Low-confidence images can therefore be placed into a review queue instead of being automatically trusted.

### Result

The system supports human-in-the-loop validation for uncertain AI outputs.

---

## Stage 10 — Production Reliability

### Goal

Improve reliability and prepare the system for repeated API requests and larger workloads.

### Idempotency

Added an `idempotency_keys` table.

The image creation endpoint accepts:

```text
Idempotency-Key
```

Repeated requests using the same key return the existing image/job instead of creating duplicates.

This was tested with repeated requests and a race-safe duplicate scenario.

### Database Indexes

Added indexes for frequently queried fields:

```text
image_processing_jobs.image_id
images.review_status
images.needs_review
```

These indexes support common job and review-queue queries.

### Result

The backend became safer for repeated requests and more efficient for common production queries.

---

## Stage 11 — AI Usage Tracking and Budget Guard

### Goal

Track AI operations and prevent uncontrolled AI usage.

### Implementation

Added an `ai_usage_logs` table containing:

```text
operation
provider
model
success
duration_ms
estimated_cost
created_at
```

Each successful or failed AI operation can record:

* Provider
* Model
* Operation type
* Execution duration
* Success/failure
* Estimated cost

Added a configurable AI budget:

```text
AI_BUDGET_LIMIT
```

and per-operation estimates:

```text
VISION_COST_PER_CALL
EMBEDDING_COST_PER_CALL
```

The system checks the projected cost before starting an AI operation.

### Budget Guard Behavior

If the next operation would exceed the configured budget, it is rejected before the AI call begins.

Budget errors are treated as permanent failures rather than retryable infrastructure failures.

### Result

The system has an explicit AI budget-control mechanism and persistent AI usage records.

---

## Stage 12 — Evaluation Suite

### Goal

Create a reproducible evaluation suite for the core matching behavior.

### Implementation

Created:

```text
evaluation/
├── dataset.json
└── evaluate.py
```

The evaluation dataset contains ten cases covering:

* Correct fox matching
* Correct wolf matching
* Correct lion matching
* Fox/wolf mismatch
* Fox/lion mismatch
* Wolf/fox mismatch
* Lion/fox mismatch
* Low-confidence image
* Missing dog match
* Missing cat match

### Evaluation Results

The final evaluation produced:

```text
Top-1 Precision: 3/3 = 100.00%
Mismatch Guard: 4/4 passed
Low-Confidence Guard: 1/1 passed
No-Confident-Match: 2/2 passed
Overall: 10/10 tests passed
```

The evaluation confirmed that:

* Correct animal images can be accepted.
* Incorrect animal subjects are rejected.
* Low-confidence images are rejected.
* The system can return no confident match when an appropriate image does not exist.

### Result

The core matching behavior is evaluated using a reproducible test dataset rather than only manual demonstrations.

---

## Stage 13 — Automated Testing and API Verification

### Goal

Add automated software tests and verify the API as a complete application.

### Testing Dependencies

Added:

```text
pytest
httpx
```

The Docker image installs these dependencies so tests can run inside the same environment as the application.

### Automated Tests

Created:

```text
tests/
├── test_health.py
├── test_validation.py
└── test_mismatch_guard.py
```

The test suite covers:

### Health and Root API

* Root endpoint
* Health endpoint

### Validation and Error Handling

* Missing image
* Missing job
* Missing idempotency key
* Invalid image URL
* Missing image for review
* Invalid review decision
* Missing blog post

### Mismatch Guard

* Correct subject accepted
* Wrong subject rejected
* Low similarity rejected
* Low confidence rejected
* Missing confidence rejected

### Final Pytest Result

The complete automated test suite produced:

```text
14 passed
```

The evaluation suite continued to produce:

```text
10/10 tests passed
100% top-1 precision
```

### API Verification

The final OpenAPI route verification confirmed:

```text
/images/
/images/{image_id}/review
/images/jobs/{job_id}
/images/review/pending
/images/{image_id}
/blog-posts/
/blog-posts/{post_id}/matches
/
/health
```

### Result

The project has both:

* Automated software tests for backend behavior.
* A separate evaluation suite for AI image-matching behavior.

---

# Engineering Decisions and Lessons

## Local AI Instead of Cloud AI

The initial vision-model approach used Gemini, but local development encountered API access restrictions.

The project was adapted to Ollama and local models instead of weakening the security of the development environment or relying on inaccessible credentials.

This also made local testing possible without requiring a paid AI API.

---

## Structured AI Output

The vision model is not trusted to return arbitrary text.

Its output is validated through Pydantic before being stored or used by downstream logic.

This provides a boundary between probabilistic AI output and deterministic application code.

---

## Semantic Matching Plus Explicit Rules

Vector similarity alone is not sufficient for content matching.

Related concepts such as foxes and wolves can have high semantic similarity while still representing the wrong subject.

The mismatch guard therefore combines:

```text
semantic similarity
+
AI confidence
+
explicit subject matching
```

This hybrid approach provides stronger control than semantic similarity alone.

---

## Human-in-the-Loop Review

AI confidence is treated as an uncertainty signal rather than absolute truth.

Low-confidence images can be flagged for human review, providing a mechanism for correcting or rejecting uncertain AI-generated metadata.

---

## Retry Only Temporary Failures

Not every error should be retried.

The system distinguishes temporary infrastructure failures from permanent errors.

For example:

```text
HTTP 500 → retry
HTTP 429 → retry
timeout → retry
HTTP 404 → do not retry
```

This prevents unnecessary repeated work.

---

## AI Budget Protection

AI calls are treated as potentially costly operations.

The system checks the budget before starting an AI operation and records usage information for completed calls.

This provides a foundation for monitoring and controlling AI-related operational costs.

---

# Final Project State

The completed backend contains:

```text
FastAPI
PostgreSQL
SQLAlchemy
Alembic
pgvector
Ollama / LLaVA
Ollama / nomic-embed-text
Pydantic
Docker
pytest
```

The major capabilities are:

* Image ingestion
* Background image processing
* Vision-based metadata extraction
* Structured AI validation
* Confidence scoring
* Embedding generation
* Vector similarity search
* Semantic image matching
* Subject mismatch protection
* Low-confidence rejection
* Human review
* Idempotent image creation
* Retry handling
* Database indexing
* AI usage tracking
* AI budget protection
* Automated evaluation
* Automated API/service tests
* Dockerized development and testing

The final evaluation and automated test results demonstrate that the implemented matching and protection mechanisms behave as expected on the project's evaluation dataset.
