# ASC 842 Calculator Deployment Guide

## Local Development

To run the application locally:

```bash
cd /Users/INSTOOL/Projects/asc842
./start.sh
```

The app will be available at: http://localhost:5000

## Render Deployment

### Prerequisites
1. GitHub repository with the ASC 842 code
2. Render account

### Deployment Steps

1. **Push to GitHub**
   ```bash
   cd /Users/INSTOOL/Projects/asc842
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **Deploy on Render**
   - Go to https://dashboard.render.com
   - Click "New +" → "Web Service"
   - Connect your GitHub repo
   - Render will auto-detect the `render.yaml` configuration
   - Click "Create Web Service"

3. **Configuration**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Environment: Python 3.11.0

### Files Required for Deployment
- ✅ `requirements.txt` - Python dependencies
- ✅ `render.yaml` - Render configuration
- ✅ `wsgi.py` - WSGI entry point
- ✅ `app.py` - Main Flask application
- ✅ `asc842_calculator.py` - Core calculation logic

### Environment Variables
No additional environment variables required for basic deployment.

### Post-Deployment
Your app will be available at:
`https://asc842-calculator.onrender.com`

### Quick Commands

**Start locally:**
```bash
./start.sh
```

**Test before deployment:**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
gunicorn app:app
```

**View logs:**
Check Render dashboard for real-time logs and metrics.