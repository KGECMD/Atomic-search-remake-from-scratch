# Deployment Guide for Atomic Search

## 🚂 Railway Deployment (Recommended)

### Step 1: Connect Repository
1. Go to [Railway](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository

### Step 2: Configure Deployment
Railway will auto-detect the `Dockerfile`. No additional configuration needed!

### Step 3: Environment Variables (Optional)
Add these in Railway dashboard if needed:
- `SECRET_KEY`: Your secret key for sessions
- `PORT`: 8080 (default)

### Step 4: Deploy
Click "Deploy" - Railway will build and deploy automatically.

### Branch to Use
**Use: `master` branch**

---

## 🐳 Docker Deployment

### Build
```bash
docker build -t atomic-search .
```

### Run
```bash
docker run -d \
  -p 8080:8080 \
  -e SECRET_KEY=your-secret-key \
  atomic-search
```

### Docker Compose
```yaml
version: '3.8'
services:
  atomic-search:
    build: .
    ports:
      - "8080:8080"
    environment:
      - SECRET_KEY=your-secret-key
      - PORT=8080
    restart: unless-stopped
```

---

## 💻 Local Development

### Prerequisites
- Python 3.10+
- pip

### Setup

```bash
# Clone repository
git clone https://github.com/KGECMD/Atomic-search-remake-from-scratch.git
cd Atomic-search-remake-from-scratch

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
python -m atomic_search.main
```

The app will be available at: `http://localhost:8080`

### Using Gunicorn (Production-like)
```bash
pip install gunicorn
gunicorn 'atomic_search.main:app' --bind 0.0.0.0:8080 --workers 2
```

---

## ☁️ Other Cloud Platforms

### Heroku
```bash
heroku create your-app-name
heroku container:push web
heroku container:release web
```

### Render
1. Connect GitHub repo to Render
2. Select "Web Service"
3. Set build command: (empty - uses Dockerfile)
4. Set start command: `gunicorn 'atomic_search.main:app' --bind 0.0.0.0:$PORT --workers 2`

### Fly.io
```bash
fly launch
fly deploy
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8080 | Server port |
| `SECRET_KEY` | auto | Session secret key |
| `DEBUG` | false | Debug mode |
| `HOST` | 0.0.0.0 | Host to bind |

### Features
- All features work out of the box
- No external services required for basic operation
- Optional: Redis for caching, PostgreSQL for data

---

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Find and kill the process
lsof -i :8080
kill -9 <PID>
```

### Dependencies Not Installing
```bash
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir
```

### App Not Starting
Check logs:
```bash
python -m atomic_search.main 2>&1 | tee app.log
```

---

## 📊 Health Check
After deployment, verify with:
```bash
curl https://your-domain/health
```

Should return:
```json
{"status": "healthy", "service": "atomic-search", "version": "1.0.0"}
```

---

## 🔒 Security Notes

- Change `SECRET_KEY` in production
- Use HTTPS (Railway provides this automatically)
- Consider rate limiting for public deployments
- Review CORS settings in `app/__init__.py`

---

## 📞 Support

For issues, open a GitHub issue at:
https://github.com/KGECMD/Atomic-search-remake-from-scratch/issues
