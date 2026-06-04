# Enterprise RAG Chatbot — Docker & Deployment Guide

## Project Structure

After adding the deployment files, your repo should look like:

```
Enterprise-RAG-Chatbot-main/
├── Dockerfile                  ← improved (multi-stage, healthcheck, non-root)
├── docker-compose.yml          ← local / staging
├── docker-compose.prod.yml     ← production (with Nginx)
├── nginx.conf                  ← reverse proxy config
├── .env.example                ← copy to .env and fill in keys
├── .dockerignore
├── requirements.txt
└── enterprise-rag-chatbot/
    ├── main.py
    ├── app/
    ├── ingestion/
    ├── retrieval/
    └── ...
```

---

## Step 1 — Set up your environment file

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY (required)
nano .env
```

---

## Step 2 — Local development (quick start)

```bash
# Build and run
docker compose up --build

# App is available at:
#   http://localhost:8501
```

To run in the background:

```bash
docker compose up -d --build

# View logs
docker compose logs -f

# Stop
docker compose down
```

---

## Step 3 — Production deployment (with Nginx)

### Option A — VPS / Cloud VM (AWS EC2, DigitalOcean, etc.)

**1. Install Docker on the server**

```bash
# Ubuntu / Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

**2. Copy files to server**

```bash
# From your local machine
scp -r . user@your-server-ip:/home/user/rag-chatbot/
ssh user@your-server-ip
cd /home/user/rag-chatbot
cp .env.example .env && nano .env   # add your API keys
```

**3. Launch production stack**

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

App is now accessible at `http://your-server-ip` via Nginx.

---

### Option B — Railway (one-click PaaS)

1. Push your code to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Set environment variables in the Railway dashboard:
   - `GROQ_API_KEY` = your key
   - `PORT` = 8501
4. Railway auto-detects the `Dockerfile` and builds it

**Note:** Railway's ephemeral filesystem means ChromaDB data won't survive redeployments without a persistent volume or external DB.

---

### Option C — Render

1. Push to GitHub
2. New Web Service → Connect repo
3. Runtime: **Docker**
4. Set env vars: `GROQ_API_KEY`
5. Port: `8501`
6. Add a **Disk** (persistent volume) mounted at `/app/enterprise-rag-chatbot/chroma_db`

---

### Option D — Google Cloud Run

```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT/rag-chatbot

# Deploy
gcloud run deploy rag-chatbot \
  --image gcr.io/YOUR_PROJECT/rag-chatbot \
  --platform managed \
  --port 8501 \
  --memory 4Gi \
  --set-env-vars GROQ_API_KEY=your_key_here \
  --allow-unauthenticated
```

**Note:** Cloud Run is stateless — ChromaDB won't persist. For persistence, mount a Cloud Filestore NFS volume or switch to a managed vector DB (e.g., Pinecone, Weaviate Cloud).

---

## SSL / HTTPS (production)

Using Certbot with Nginx:

```bash
# Install certbot on your server
sudo apt install certbot python3-certbot-nginx

# Get a certificate (replace with your domain)
sudo certbot --nginx -d your-domain.com

# Certbot auto-updates nginx.conf with SSL settings
# Then restart nginx
docker compose -f docker-compose.prod.yml restart nginx
```

Or manually: place `fullchain.pem` and `privkey.pem` in `./ssl/` and uncomment the HTTPS block in `nginx.conf`.

---

## Managing persistent data (ChromaDB + Feedback)

```bash
# List volumes
docker volume ls

# Backup ChromaDB
docker run --rm \
  -v enterprise-rag-chatbot-main_chroma_data:/data \
  -v $(pwd):/backup alpine \
  tar czf /backup/chroma_backup_$(date +%Y%m%d).tar.gz -C /data .

# Restore
docker run --rm \
  -v enterprise-rag-chatbot-main_chroma_data:/data \
  -v $(pwd):/backup alpine \
  tar xzf /backup/chroma_backup_YYYYMMDD.tar.gz -C /data
```

---

## Useful commands

```bash
# Rebuild after code changes
docker compose up -d --build

# Shell into running container
docker exec -it rag-chatbot bash

# View resource usage
docker stats rag-chatbot

# Remove everything (WARNING: deletes volumes too)
docker compose down -v
```

---

## Environment variables reference

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | ✅ Yes | LLM inference via Groq |
| `COHERE_API_KEY` | Optional | Enables reranking for better retrieval |
| `OPENAI_API_KEY` | Optional | For RAGAS evaluation only |
| `HOST_PORT` | Optional | Host port (default: 8501) |

---

## Troubleshooting

**Container exits immediately**
```bash
docker compose logs rag-chatbot
# Usually a missing GROQ_API_KEY or import error
```

**Port 8501 already in use**
```bash
# Change port in .env
HOST_PORT=8502
docker compose up -d
```

**ChromaDB "no space left on device"**
```bash
docker system prune -f   # clean build cache
docker volume inspect enterprise-rag-chatbot-main_chroma_data
```

**Sentence-transformers slow first start**  
Normal — the model downloads ~90MB on first run. It's cached in the Docker layer on subsequent builds.