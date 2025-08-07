# 🚀 Backend Deployment Guide

Your frontend is now deployed successfully! The "Failed to fetch" error occurs because your backend API isn't deployed yet. Here's how to fix it:

## 🎯 Quick Solutions

### Option 1: Deploy Backend to Railway (Recommended)

1. **Install Railway CLI:**

   ```bash
   npm install -g @railway/cli
   ```

2. **Login and deploy:**

   ```bash
   railway login
   cd TrustLens.AI  # Make sure you're in the project root
   railway init
   railway up
   ```

3. **Set environment variables:**

   ```bash
   railway variables set ETHERSCAN_API_KEY=your_etherscan_key
   railway variables set GEMINI_API_KEY=your_gemini_key
   railway variables set ENVIRONMENT=production
   railway variables set FRONTEND_ORIGINS=https://your-netlify-site.netlify.app
   ```

4. **Get your Railway URL** (something like `https://your-app.railway.app`)

### Option 2: Deploy Backend to Render

1. **Create `render.yaml` in project root:**

   ```yaml
   services:
     - type: web
       name: trustlens-backend
       env: python
       buildCommand: pip install -r requirements.txt
       startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
       envVars:
         - key: ETHERSCAN_API_KEY
           sync: false
         - key: GEMINI_API_KEY
           sync: false
         - key: ENVIRONMENT
           value: production
   ```

2. **Connect your GitHub repo to Render**
3. **Set environment variables in Render dashboard**

### Option 3: Deploy Backend to Heroku

1. **Create `Procfile` in project root:**

   ```
   web: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

2. **Deploy:**
   ```bash
   heroku create your-app-name
   heroku config:set ETHERSCAN_API_KEY=your_key
   heroku config:set GEMINI_API_KEY=your_key
   heroku config:set ENVIRONMENT=production
   git push heroku main
   ```

## 🔗 Connect Frontend to Backend

After deploying your backend, you need to update your frontend configuration:

### Method 1: Update the HTML file (Quick Fix)

1. **Edit `frontend/app.html`** and replace this line:

   ```javascript
   : 'https://your-backend-url.com', // Replace this with your actual backend URL
   ```

   With your actual backend URL:

   ```javascript
   : 'https://your-railway-app.railway.app', // Your actual backend URL
   ```

2. **Commit and push:**
   ```bash
   git add .
   git commit -m "Update API URL for production"
   git push origin main
   ```

### Method 2: Use Netlify Environment Variables (Better)

1. **Go to your Netlify dashboard**
2. **Site settings → Environment variables**
3. **Add these variables:**
   ```
   VITE_API_URL=https://your-backend-url.com
   VITE_ENVIRONMENT=production
   ```
4. **Redeploy your site**

## 🧪 Test Your Setup

1. **Check backend health:**

   ```bash
   curl https://your-backend-url.com/health
   ```

2. **Test API endpoint:**

   ```bash
   curl -X POST https://your-backend-url.com/api/v2/analyze \
     -H "Content-Type: application/json" \
     -d '{"address":"0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"}'
   ```

3. **Check frontend console** for any CORS errors

## 🔧 Common Issues & Fixes

### Issue: CORS Errors

**Fix:** Update your backend's CORS settings in `main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-netlify-site.netlify.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Issue: API Key Missing

**Fix:** Make sure you set environment variables on your hosting platform:

- `ETHERSCAN_API_KEY` - Get from etherscan.io
- `GEMINI_API_KEY` - Get from Google AI Studio (optional)

### Issue: Backend Not Starting

**Fix:** Check the logs on your hosting platform and ensure:

- All dependencies are installed
- Port is set correctly (`$PORT` environment variable)
- Python version is compatible

## 🎯 Expected Result

After completing these steps:

1. ✅ Backend API running on your hosting platform
2. ✅ Frontend connecting to the correct API URL
3. ✅ Wallet analysis working end-to-end
4. ✅ No more "Failed to fetch" errors

## 📞 Need Help?

If you encounter issues:

1. Check the browser console for error messages
2. Verify your backend is accessible at the URL
3. Ensure CORS is configured correctly
4. Test API endpoints directly with curl

Your TrustLens.AI app will be fully functional once the backend is deployed! 🎉
