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
                      │    PostgreSQL + pgvector              │
                      │                                      │
                      │  grab_ids   ── embedding (Vector 128) │
                      │  images     ── file_path, metadata    │
                      │  image_grab_ids ── many-to-many link  │
                      └──────────────────────────────────────┘
```

---

## Prerequisites

- **Docker** & **Docker Compose** (for PostgreSQL + pgvector)
- **Python 3.10+**
- **pip** (or a virtualenv manager)

---

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd grabpic
```

### 2. Start PostgreSQL with pgvector

```bash
docker-compose up -d
```

This starts a PostgreSQL 16 instance with the pgvector extension on port `5432`.

### 3. Install Python dependencies

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 4. Run the server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.  
Interactive docs at `http://localhost:8000/docs`.

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

---

### `GET /images/{grab_id}`

Retrieve all photos linked to a specific GrabID.

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

---

## Database Schema

| Table | Description |
|-------|-------------|
| `grab_ids` | Each row = a unique face identity. Stores a 128-dim embedding vector. |
| `images` | Each row = an ingested photo. Stores file path and original filename. |
| `image_grab_ids` | Many-to-many link between images and face identities. Also stores the `face_area` (bounding box). |

### Key columns

- `grab_ids.embedding` — `Vector(128)` column (pgvector). The 128-dimensional FaceNet embedding.
- `image_grab_ids.face_area` — JSON column: `{"x": int, "y": int, "w": int, "h": int}` bounding box of the detected face.

---

## How Face Matching Works

1. **Embedding extraction**: When a photo is ingested, DeepFace (FaceNet model) produces a 128-dimensional embedding vector for each detected face.

2. **Cosine similarity**: To find a matching identity, we use pgvector's cosine distance operator (`<=>`):
   ```sql
   SELECT id, (embedding <=> CAST(:vec AS vector)) AS distance
   FROM grab_ids
   ORDER BY distance
   LIMIT 1
   ```

3. **Threshold**: If the cosine distance is below `SIMILARITY_THRESHOLD` (default `0.40`), the face is considered a match and mapped to the existing GrabID. Otherwise, a new GrabID is created.

4. **Selfie auth**: The same process is used for selfie authentication — extract the embedding, find the nearest neighbor, and check if the distance is below the threshold.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://grabpic:grabpic_secret@localhost:5432/grabpic_db` | Async database URL |
| `SYNC_DATABASE_URL` | `postgresql+psycopg2://grabpic:grabpic_secret@localhost:5432/grabpic_db` | Sync URL for Alembic |
| `UPLOAD_DIR` | `./uploads` | Directory for stored images |
| `SIMILARITY_THRESHOLD` | `0.40` | Cosine distance threshold for face matching |

---

## Alembic Migrations

Generate a new migration after model changes:

```bash
alembic revision --autogenerate -m "describe your changes"
alembic upgrade head
```

---

## License

MIT
