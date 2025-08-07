# 🚂 Railway Deployment Guide - Website Method

## 📋 Prerequisites

Before deploying, make sure you have:
- [x] GitHub account with your TrustLens.AI repository
- [x] Etherscan API key (get free at [etherscan.io/apis](https://etherscan.io/apis))
- [x] Gemini API key (optional, get at [Google AI Studio](https://makersuite.google.com/app/apikey))

## 🚀 Step-by-Step Railway Deployment

### Step 1: Access Railway
1. Go to [railway.app](https://railway.app)
2. Click **"Start a New Project"**
3. Sign up/login with your GitHub account

### Step 2: Connect Your Repository
1. Click **"Deploy from GitHub repo"**
2. Select your **TrustLens.AI** repository
3. Railway will automatically detect it's a Python project

### Step 3: Configure Build Settings
Railway should automatically detect your Python app, but verify these settings:

**Build Configuration:**
- **Root Directory:** `/` (leave empty - it's the root)
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Step 4: Set Environment Variables
In your Railway dashboard, go to **Variables** tab and add these:

#### Required Variables:
```
ETHERSCAN_API_KEY=your_etherscan_api_key_here
ENVIRONMENT=production
DEBUG=false
```

#### Optional but Recommended:
```
GEMINI_API_KEY=your_gemini_api_key_here
CACHE_TTL=300
REQUEST_TIMEOUT=30
RATE_LIMIT=100/minute
```

#### CORS Configuration (Important!):
```
FRONTEND_ORIGINS=https://your-netlify-site.netlify.app
```
*Replace with your actual Netlify URL*

### Step 5: Deploy
1. Click **"Deploy"**
2. Railway will build and deploy your app
3. Wait for deployment to complete (usually 2-3 minutes)
4. You'll get a URL like: `https://your-app.railway.app`

### Step 6: Test Your Backend
1. **Health Check:**
   Visit: `https://your-app.railway.app/health`
   
2. **API Documentation:**
   Visit: `https://your-app.railway.app/docs`

3. **Test API Call:**
   ```bash
   curl -X POST https://your-app.railway.app/api/v2/analyze \
     -H "Content-Type: application/json" \
     -d '{"address":"0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"}'
   ```

## 🔗 Connect Frontend to Backend

### Method 1: Update app.html (Quick)
1. **Edit `frontend/app.html`**
2. **Find this line:**
   ```javascript
   : 'https://your-backend-url.com', // Replace this with your actual backend URL
   ```
3. **Replace with your Railway URL:**
   ```javascript
   : 'https://your-app.railway.app', // Your Railway backend URL
   ```
4. **Commit and push:**
   ```bash
   git add .
   git commit -m "Connect frontend to Railway backend"
   git push origin main
   ```

### Method 2: Use Netlify Environment Variables (Better)
1. **Go to Netlify Dashboard**
2. **Site settings → Environment variables**
3. **Add:**
   ```
   VITE_API_URL=https://your-app.railway.app
   VITE_ENVIRONMENT=production
   ```
4. **Redeploy your Netlify site**

## 🔧 Troubleshooting

### Issue: Build Fails
**Check these:**
- Ensure `requirements.txt` is in the root directory ✅
- Verify `main.py` is in the root directory ✅
- Check Railway build logs for specific errors

### Issue: App Crashes on Start
**Common fixes:**
- Ensure `PORT` environment variable is not set (Railway sets this automatically)
- Check that all required dependencies are in `requirements.txt`
- Verify your Etherscan API key is valid

### Issue: CORS Errors
**Fix:**
- Add your Netlify URL to `FRONTEND_ORIGINS` environment variable
- Format: `https://your-site.netlify.app` (no trailing slash)

### Issue: API Returns Errors
**Check:**
- Etherscan API key is valid and has credits
- Environment variables are set correctly
- Backend logs in Railway dashboard

## 📊 Railway Dashboard Features

**Useful tabs in your Railway dashboard:**
- **Deployments:** See build and deployment history
- **Metrics:** Monitor CPU, memory, and network usage
- **Logs:** View application logs and errors
- **Variables:** Manage environment variables
- **Settings:** Configure domains, scaling, etc.

## 🎯 Expected Result

After successful deployment:
1. ✅ Backend API running on Railway
2. ✅ Health endpoint accessible
3. ✅ API documentation available
4. ✅ Frontend connecting successfully
5. ✅ Wallet analysis working end-to-end

## 💡 Pro Tips

1. **Custom Domain:** Railway allows custom domains in Settings
2. **Scaling:** Railway auto-scales based on usage
3. **Logs:** Use the Logs tab to debug issues
4. **Metrics:** Monitor your app's performance
5. **Redis:** Add Redis service for caching (optional)

## 🆘 Need Help?

If you encounter issues:
1. Check Railway build logs
2. Verify environment variables are set
3. Test API endpoints directly
4. Check CORS configuration
5. Ensure Etherscan API key is working

Your TrustLens.AI backend will be live on Railway! 🎉

## 📝 Files I've Created for Railway:
- `railway.json` - Railway configuration
- `Procfile` - Process definition
- `.env.railway` - Environment variables template

Everything is ready for deployment! 🚀