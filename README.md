# AI Image Understanding & Content Matching Engine

An AI-powered backend system that analyzes images, extracts structured metadata, generates semantic embeddings, and matches images to blog posts.

The system combines vision AI, vector similarity search, deterministic mismatch protection, background processing, human review, AI cost controls, and automated evaluation.

## Overview

The system is designed to answer a simple question:

> Which image is the most appropriate match for a given piece of content?

Instead of relying only on keyword matching, the system:

1. Receives an image URL.
2. Processes the image in a background job.
3. Uses a vision model to identify the image.
4. Validates the AI-generated metadata.
5. Generates a semantic embedding.
6. Stores the metadata and embedding in PostgreSQL.
7. Generates embeddings for blog posts.
8. Searches for semantically similar images.
9. Applies a mismatch guard before accepting a match.
10. Rejects low-confidence or incorrect subjects.
11. Allows uncertain images to be reviewed by a human.

## Architecture

    +---------------------+
    |      FastAPI API    |
    +----------+----------+
               |
    +----------+----------+----------------+
    |                     |                |
    v                     v                v
    Image Ingestion       Blog Post API    Review API
    |                     |
    v                     v
    Background Job        Embedding
    |                     Generation
    v                         |
    Vision AI                  |
    (LLaVA)                    |
    |                          |
    v                          |
    Pydantic Validation        |
    |                          |
    v                          |
    Image Metadata             |
    |                          |
    v                          |
    Embedding Generation <-----+
    |
    v
    +-----------------------+
    | PostgreSQL + pgvector |
    +-----------+-----------+
                |
                v
        Cosine Similarity
                |
                v
         Mismatch Guard
                |
        +-------+--------+
        |                |
     Accepted          Rejected
        |                |
        v                v
    Image Match      Explanation /
                     No Confident Match

## Technology Stack

| Component | Technology |
|---|---|
| Backend | FastAPI |
| Language | Python |
| Database | PostgreSQL |
| Vector Search | pgvector |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Vision AI | Ollama + LLaVA |
| Embeddings | Ollama + nomic-embed-text |
| Validation | Pydantic |
| Testing | pytest |
| API Testing | HTTPX / FastAPI TestClient |
| Containerization | Docker / Docker Compose |

## Core Features

### 1. Image Ingestion

Images can be submitted through:

    POST /images/

The endpoint creates an image record and a background processing job.

The API also supports idempotency keys to prevent duplicate processing when the same request is submitted repeatedly.

### 2. Structured Vision Analysis

The vision model extracts:

    subject
    category
    attributes
    caption
    confidence

Example:

    {
      "subject": "fox",
      "category": "animal",
      "attributes": [
        "orange fur",
        "pointed ears"
      ],
      "caption": "A fox in a natural outdoor environment.",
      "confidence": 0.9
    }

The output is validated using Pydantic before being used by the application.

Confidence is constrained to the range:

    0.0 - 1.0

### 3. Background Processing

Image analysis runs through a background processing workflow.

The processing pipeline is:

    Image URL
        |
        v
    Download Image
        |
        v
    Vision Analysis
        |
        v
    Validate Metadata
        |
        v
    Generate Embedding
        |
        v
    Store Results
        |
        v
    Complete Job

Jobs maintain processing state and attempt counts.

### 4. Retry Handling

Temporary failures can be retried automatically.

Retryable errors include:

- Connection errors
- Timeouts
- HTTP 429
- HTTP 5xx

Permanent errors such as HTTP 404 responses are not retried.

The worker uses exponential backoff with jitter and supports a maximum of three attempts.

### 5. Semantic Embeddings

Image metadata is converted into a 768-dimensional embedding using:

    nomic-embed-text

Blog posts are embedded using the same embedding model.

The resulting vectors are stored in PostgreSQL using pgvector.

### 6. Semantic Image Matching

For a blog post, the system searches the image embeddings using cosine distance.

The similarity score is calculated as:

    similarity = 1 - cosine_distance

Candidates are ranked by similarity.

### 7. Mismatch Guard

Semantic similarity alone is not trusted to determine whether an image is correct.

For example, a wolf image can be semantically similar to a fox article because both are animals.

The mismatch guard therefore checks:

    Semantic Similarity
            +
    Image Confidence
            +
    Expected Subject
            +
    Actual Subject

Default thresholds:

    Similarity threshold:       0.70
    Minimum image confidence:   0.70

A candidate is rejected when:

- Similarity is below the threshold.
- Confidence is missing.
- Confidence is below the minimum.
- The image subject does not match the expected subject.

Rejected candidates include a human-readable reason.

Example:

    Image subject "wolf" does not match expected subject "fox".

### 8. Human Review

Images with low confidence can be flagged for human review.

Available endpoints:

    POST /images/{image_id}/review
    GET  /images/{image_id}/review
    GET  /images/review/pending

Review decisions are:

    approved
    rejected

A review reason and timestamp are also stored.

### 9. Idempotency

Image creation supports:

    Idempotency-Key

Repeated requests with the same key return the existing image/job instead of creating another one.

This protects the system from duplicate requests and accidental repeated processing.

### 10. AI Usage and Budget Tracking

AI operations are recorded in the database.

Tracked information includes:

- Operation
- Provider
- Model
- Success/failure
- Duration
- Estimated cost
- Timestamp

The system also supports a configurable AI budget.

Before an AI operation begins, the projected cost is checked against the configured budget.

Example configuration:

    AI_BUDGET_LIMIT=1.00
    VISION_COST_PER_CALL=0.00
    EMBEDDING_COST_PER_CALL=0.00

If an operation would exceed the configured budget, it is blocked before the AI call is made.

## API Endpoints

### System

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | API information |
| GET | `/health` | Health check |

### Images

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/images/` | Submit an image |
| GET | `/images/{image_id}` | Retrieve image information |
| GET | `/images/jobs/{job_id}` | Check processing job |
| GET | `/images/review/pending` | List images awaiting review |
| POST | `/images/{image_id}/review` | Approve/reject an image |
| GET | `/images/{image_id}/review` | Retrieve review information |

### Blog Posts

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/blog-posts/` | Create a blog post |
| GET | `/blog-posts/{post_id}/matches` | Retrieve matching images |

## Project Structure

    ai-image-content-matching-engine/
    |
    +-- app/
    |   +-- api/
    |   |   +-- routes/
    |   |       +-- images.py
    |   |       +-- blog_posts.py
    |   |
    |   +-- core/
    |   |
    |   +-- db/
    |   |   +-- base.py
    |   |   +-- database.py
    |   |   +-- dependencies.py
    |   |
    |   +-- models/
    |   |   +-- image.py
    |   |   +-- job.py
    |   |   +-- blog_post.py
    |   |   +-- idempotency.py
    |   |   +-- ai_usage.py
    |   |
    |   +-- schemas/
    |   |   +-- image.py
    |   |   +-- vision.py
    |   |   +-- review.py
    |   |
    |   +-- services/
    |   |   +-- vision_service.py
    |   |   +-- embedding_service.py
    |   |   +-- image_processing_service.py
    |   |   +-- matching_service.py
    |   |   +-- mismatch_guard.py
    |   |   +-- ai_usage_service.py
    |   |   +-- ai_budget_service.py
    |   |
    |   +-- workers/
    |   |   +-- image_worker.py
    |   |
    |   +-- main.py
    |   +-- vision_manual.py
    |
    +-- alembic/
    |   +-- versions/
    |
    +-- evaluation/
    |   +-- dataset.json
    |   +-- evaluate.py
    |
    +-- tests/
    |   +-- test_health.py
    |   +-- test_validation.py
    |   +-- test_mismatch_guard.py
    |
    +-- .env.example
    +-- .gitignore
    +-- BUILDLOG.md
    +-- EVIDENCE.md
    +-- capstone.yaml
    +-- Dockerfile
    +-- docker-compose.yml
    +-- alembic.ini
    +-- requirements.txt
    +-- README.md

## Running the Project

### Prerequisites

The project uses:

- Docker
- Docker Compose
- Ollama
- LLaVA
- nomic-embed-text

Pull the required Ollama models:

    ollama pull llava
    ollama pull nomic-embed-text

### Environment Configuration

Create a local `.env` file based on `.env.example`.

Example:

    AI_BUDGET_LIMIT=1.00
    VISION_COST_PER_CALL=0.00
    EMBEDDING_COST_PER_CALL=0.00

The database connection is configured by Docker Compose for the API container.

### Start the Application

Build and start the containers:

    docker compose up -d --build

Check the running containers:

    docker compose ps

The API is available at:

    http://localhost:8000

FastAPI's interactive API documentation is available at:

    http://localhost:8000/docs

## Running Tests

Run the complete automated test suite:

    docker compose exec api python -m pytest -v

Expected result:

    14 passed

## Running the Evaluation

Run the AI matching evaluation:

    docker compose exec api python evaluation/evaluate.py

The evaluation covers:

- Correct subject matching
- Cross-subject mismatch rejection
- Low-confidence rejection
- No-confident-match behavior

Final result:

    Top-1 Precision: 3/3 = 100.00%
    Mismatch Guard: 4/4 passed
    Low-Confidence Guard: 1/1 passed
    No-Confident-Match: 2/2 passed
    Overall: 10/10 tests passed

## Reliability Features

The backend includes several production-oriented safeguards:

- Request idempotency
- Background processing
- Job status tracking
- Retryable versus permanent error handling
- Exponential backoff
- Retry jitter
- Database indexes
- Environment-based configuration
- AI budget protection
- AI usage logging
- Human review workflow

## Database Migrations

The project uses Alembic for database schema management.

Check the current migration:

    docker compose exec api alembic current

Apply migrations:

    docker compose exec api alembic upgrade head

## Evaluation and Evidence

The repository includes dedicated evaluation and evidence files:

    evaluation/dataset.json
    evaluation/evaluate.py
    EVIDENCE.md
    BUILDLOG.md

`evaluation/dataset.json` contains the labeled evaluation cases.

`evaluation/evaluate.py` executes the evaluation and reports the results.

`EVIDENCE.md` records the final evaluation output.

`BUILDLOG.md` documents the engineering process and major implementation decisions.

## Current Results

### Automated Tests

    14/14 tests passed

### AI Evaluation

    10/10 evaluation cases passed

### Top-1 Precision

    100%

### Mismatch Protection

    4/4 passed

### Low-Confidence Protection

    1/1 passed

### No-Confident-Match Cases

    2/2 passed

## Project Status

The core backend implementation is complete.

The system currently provides:

- AI image understanding
- Structured metadata extraction
- Confidence scoring
- Semantic embeddings
- Vector similarity matching
- Subject mismatch protection
- Background processing
- Retry handling
- Human review
- Idempotency
- AI usage tracking
- AI budget protection
- Automated testing
- Automated evaluation
- Docker-based deployment

The project is designed as a backend-first AI engineering system, with the API and evaluation system forming the core implementation.