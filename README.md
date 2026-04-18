# 📸 Grabpic

High-performance facial recognition backend for large-scale events.  
Ingest thousands of event photos, automatically detect and cluster faces, and let attendees retrieve their photos by taking a selfie.

---

## Architecture

```
┌─────────────┐       ┌──────────────────────────────────────┐
│   Client    │       │           Grabpic API (FastAPI)       │
│  (curl/app) │──────▶│                                      │
└─────────────┘       │  POST /ingest ──▶ Save images        │
                      │                   Extract embeddings  │
                      │                   Cluster into GrabIDs│
                      │                                      │
                      │  POST /auth/selfie ──▶ Extract face   │
                      │                       Match via cosine│
                      │                       Return GrabID   │
                      │                                      │
                      │  GET /images/{id} ──▶ Fetch photos    │
                      │                       linked to face  │
                      └──────────┬───────────────────────────┘
                                 │
                      ┌──────────▼───────────────────────────┐
                      │    PostgreSQL                         │
                      │                                      │
                      │  grab_ids   ── embedding (JSON, 512) │
                      │  images     ── file_path, metadata    │
                      │  image_grab_ids ── many-to-many link  │
                      └──────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Framework** | FastAPI (async, with Pydantic v2 schemas) |
| **Face Recognition** | InsightFace (`buffalo_l` model / ArcFace) |
| **Embeddings** | 512-dimensional vectors (stored as JSON) |
| **Similarity Matching** | NumPy cosine similarity (in-process) |
| **Database** | PostgreSQL 16 (via SQLAlchemy async + asyncpg) |
| **Migrations** | Alembic |
| **Containerization** | Docker (multi-stage) + Docker Compose |
| **Runtime** | Python 3.12, Uvicorn |

---

## Project Structure

```
vyrothon-backend/
├── app/
│   ├── __init__.py
│   ├── config.py           # Pydantic Settings (env vars / .env)
│   ├── database.py         # Async engine, session factory, init_db()
│   ├── dependencies.py     # FastAPI dependency (get_db)
│   ├── face_service.py     # InsightFace embedding extraction & matching
│   ├── main.py             # FastAPI app, CORS, lifespan, router registration
│   ├── models.py           # SQLAlchemy ORM models (GrabID, Image, ImageGrabID)
│   ├── schemas.py          # Pydantic response schemas
│   └── routes/
│       ├── __init__.py
│       ├── ingest.py       # POST /ingest
│       ├── auth.py         # POST /auth/selfie
│       └── images.py       # GET /images/{grab_id}
├── alembic/                # Alembic migration environment
├── alembic.ini
├── uploads/                # Ingested image storage (gitignored)
├── sample_images/          # Sample images for testing (gitignored)
├── Dockerfile              # Multi-stage build (Python 3.12-slim)
├── docker-compose.yml      # PostgreSQL 16 service
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Prerequisites

- **Docker** & **Docker Compose** (for PostgreSQL)
- **Python 3.10+** (Python 3.14 is verified working). If you don't have it, you can download Python from [python.org/downloads](https://www.python.org/downloads/) or use tools like `pyenv` to manage multiple versions.
- **pip** (or a virtualenv manager)

---

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd vyrothon-backend
```

### 2. Start PostgreSQL

```bash
docker-compose up -d
```

This starts a PostgreSQL 16 instance on port `5432`.

### 3. Install Python dependencies

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` to match your environment (database credentials, upload path, similarity threshold).  
See [`.env.example`](.env.example) for all available options with descriptions.

### 5. Run database migrations

```bash
alembic upgrade head
```

### 6. Run the server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.  
Interactive docs at `http://localhost:8000/docs`.

### Docker (full-stack)

Build and run the API in a container:

```bash
docker build -t grabpic .
docker run -p 8000:8000 --env DATABASE_URL=<your-db-url> grabpic
```

---

## API Endpoints

### `GET /health`

Health check.

```bash
curl http://localhost:8000/health
```

Response:
```json
{"status": "ok", "service": "grabpic"}
```

---

### `POST /ingest`

Upload one or more event photos for face detection and clustering.

```bash
curl -X POST http://localhost:8000/ingest \
  -F "images=@photo1.jpg" \
  -F "images=@photo2.jpg" \
  -F "images=@photo3.jpg"
```

Response:
```json
{
  "ingested": [
    {
      "image_id": "550e8400-e29b-41d4-a716-446655440000",
      "filename": "photo1.jpg",
      "faces_found": 3,
      "grab_ids": [
        "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "6ba7b811-9dad-11d1-80b4-00c04fd430c8",
        "6ba7b812-9dad-11d1-80b4-00c04fd430c8"
      ]
    }
  ],
  "total_images": 1,
  "total_faces_found": 3
}
```

- Only image MIME types are accepted; non-images return `422`.
- Files are saved with a UUID filename in the `uploads/` directory.

---

### `POST /auth/selfie`

Authenticate by uploading a selfie. The system finds the best matching face.

```bash
curl -X POST http://localhost:8000/auth/selfie \
  -F "selfie=@my_selfie.jpg"
```

Success response:
```json
{
  "authenticated": true,
  "grab_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "message": "Identity verified successfully"
}
```

Failure responses:
- `400` — No face detected in the selfie
- `401` — Face not recognized (not in the system)

> If multiple faces are detected in the selfie, the **largest face** (by bounding-box area) is used for matching.

---

### `GET /images/{grab_id}`

Retrieve all photos linked to a specific GrabID, ordered by most recently ingested.

```bash
curl http://localhost:8000/images/6ba7b810-9dad-11d1-80b4-00c04fd430c8
```

Response:
```json
{
  "grab_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "total_images": 2,
  "images": [
    {
      "image_id": "550e8400-e29b-41d4-a716-446655440000",
      "filename": "photo1.jpg",
      "file_path": "./uploads/550e8400-e29b-41d4-a716-446655440000.jpg",
      "face_area": {"x": 120, "y": 80, "w": 95, "h": 95},
      "ingested_at": "2026-04-18T12:00:00"
    }
  ]
}
```

- Returns `404` if the `grab_id` does not exist.

---

## Database Schema

| Table | Description |
|-------|-------------|
| `grab_ids` | Each row = a unique face identity cluster. Stores a 512-dim ArcFace embedding as JSON. |
| `images` | Each row = an ingested photo. Stores file path and original filename. |
| `image_grab_ids` | Many-to-many link between images and face identities. Also stores the `face_area` bounding box. |

### Key columns

- `grab_ids.embedding` — JSON column holding a list of 512 floats (ArcFace embedding).
- `image_grab_ids.face_area` — JSON column: `{"x": int, "y": int, "w": int, "h": int}` bounding box of the detected face.

---

## How Face Matching Works

1. **Embedding extraction**: When a photo is ingested, InsightFace (`buffalo_l` / ArcFace model) produces a **512-dimensional** embedding vector for each detected face.

2. **Cosine similarity**: All existing GrabID embeddings are loaded from the database and compared against the new embedding using NumPy cosine similarity:
   ```python
   cosine_similarity = dot(a, b) / (norm(a) * norm(b))
   ```

3. **Threshold**: If the cosine similarity is above `SIMILARITY_THRESHOLD` (default `0.50`), the face is considered a match and mapped to the existing GrabID. Otherwise, a new GrabID is created.

4. **Selfie auth**: The same process is used for selfie authentication — extract the embedding, find the nearest neighbor, and check if the similarity exceeds the threshold.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://grabpic:grabpic_secret@localhost:5432/grabpic_db` | Async database URL |
| `SYNC_DATABASE_URL` | `postgresql+psycopg2://grabpic:grabpic_secret@localhost:5432/grabpic_db` | Sync URL for Alembic |
| `UPLOAD_DIR` | `./uploads` | Directory for stored images |
| `SIMILARITY_THRESHOLD` | `0.50` | Cosine similarity threshold for face matching |

Settings are loaded via **pydantic-settings** and can be overridden with a `.env` file.

---

## Alembic Migrations

Generate a new migration after model changes:

```bash
alembic revision --autogenerate -m "describe your changes"
alembic upgrade head
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `uvicorn[standard]` | ASGI server |
| `sqlalchemy[asyncio]` | ORM (async) |
| `asyncpg` | PostgreSQL async driver |
| `psycopg2-binary` | PostgreSQL sync driver (Alembic) |
| `insightface` | Face detection & embedding (ArcFace) |
| `onnxruntime` | ONNX model inference backend |
| `opencv-python-headless` | Image I/O for InsightFace |
| `pillow` | Image processing |
| `numpy` | Cosine similarity computation |
| `alembic` | Database migrations |
| `python-multipart` | File upload support for FastAPI |
| `python-dotenv` | `.env` file loading |
| `pydantic-settings` | Typed settings from env vars |

---

## License

MIT
