# ⭐ SuperNova Search Deployment Guide

## 🚂 Railway Deployment (Recommended)

### Quick Deploy
1. Go to [Railway](https://railway.app)
2. Click **"New Project"** → **"Deploy from GitHub"**
3. Select repository: `KGECMD/Atomic-search-remake-from-scratch`
4. **Branch:** `master`
5. Railway auto-detects Dockerfile - click **Deploy**!

### Railway Settings
```
Builder: DOCKERFILE (auto-detected)
Health Check: /health
Port: 8080 (auto-set)
```

### Railway Environment
No environment variables needed! It works out of the box.

---

## 🎨 Render.com Deployment

### Docker Deployment
1. Go to [Render](https://render.com)
2. Click **"New"** → **"Web Service"**
3. Connect GitHub repo
4. Settings:
   - **Environment:** Docker
   - **Region:** Oregon (or closest)
   - **Health Check Path:** `/health`
5. Deploy!

### render.yaml (Pre-configured)
```yaml
services:
  - type: web
    name: supernova-search
    env: Docker
    dockerfilePath: ./Dockerfile
    region: oregon
    healthCheckPath: /health
```

---

## 🐳 Docker Deployment

### Build Image
```bash
docker build -t supernova-search .
```

### Run Container
```bash
docker run -d \
  -p 8080:8080 \
  --name supernova \
  -e PORT=8080 \
  supernova-search
```

### Docker Compose
```yaml
version: '3.8'
services:
  supernova:
    build: .
    ports:
      - "8080:8080"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## 💻 Local Development

### Windows
```batch
# Option 1: Double-click
start.bat

# Option 2: PowerShell
.\run.ps1

# Option 3: Manual
pip install -r requirements.txt
python -m atomic_search.main
```

### Linux/macOS
```bash
# Clone
git clone https://github.com/KGECMD/Atomic-search-remake-from-scratch.git
cd Atomic-search-remake-from-scratch

# Install & Run
pip install -r requirements.txt
python -m atomic_search.main

# Or with Gunicorn
gunicorn 'atomic_search.main:app' --bind 0.0.0.0:8080 --workers 2
```

### Access
- **URL:** http://localhost:8080
- **Health:** http://localhost:8080/health

---

## ✅ Verify Deployment

### Test Health Endpoint
```bash
curl https://your-domain.com/health
```

Expected response:
```json
{"service":"supernova-search","status":"healthy","version":"1.0.0"}
```

### Test API
```bash
curl http://localhost:8080/api/v1/stats
curl http://localhost:8080/api/v1/search/trending
```

### Test Tools
```bash
# Calculator
curl -X POST http://localhost:8080/tools/calculate \
  -H "Content-Type: application/json" \
  -d '{"expression":"sqrt(144)"}'

# Unit Converter
curl -X POST http://localhost:8080/tools/convert \
  -H "Content-Type: application/json" \
  -d '{"value":1,"from":"km","to":"m","type":"length"}'

# Currency
curl -X POST http://localhost:8080/tools/currency \
  -H "Content-Type: application/json" \
  -d '{"amount":100,"from":"USD","to":"EUR"}'
```

---

## 🔒 Privacy Features

- **Zero Telemetry** - No tracking, no analytics
- **No Cookies by Default** - Privacy-first
- **Secure Headers** - CSP, X-Frame, etc.
- **CSRF Protection** - Built-in
- **Rate Limiting** - Optional
- **Encrypted Settings** - Available

---

## 🆘 Troubleshooting

### Port Already in Use
```bash
# Linux/macOS
lsof -i :8080
kill -9 <PID>

# Windows
netstat -ano | findstr :8080
taskkill /PID <PID> /F
```

### Build Fails
```bash
# Clear cache and rebuild
docker build --no-cache -t supernova-search .
```

### App Crashes
```bash
# Check logs
python -m atomic_search.main 2>&1 | tee app.log

# Or with gunicorn
gunicorn 'atomic_search.main:app' --bind 0.0.0.0:8080 --log-level debug
```

---

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/stats` | GET | Voting stats |
| `/api/v1/search/trending` | GET | Trending searches |
| `/api/v1/search/operators` | GET | Search operators |
| `/tools/calculate` | POST | Calculator |
| `/tools/convert` | POST | Unit converter |
| `/tools/currency` | POST | Currency converter |

---

## 🔧 Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8080 | Server port |
| `SECRET_KEY` | auto | Session key |
| `DEBUG` | false | Debug mode |
| `PYTHONUNBUFFERED` | 1 | Real-time logs |

---

## 📞 Support

- **GitHub Issues:** https://github.com/KGECMD/Atomic-search-remake-from-scratch/issues
- **Documentation:** See README.md
