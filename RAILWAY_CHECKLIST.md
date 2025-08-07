# ✅ Railway Deployment Checklist

## 📋 Pre-Deployment Checklist

- [x] `main.py` is in the root directory
- [x] `requirements.txt` is in the root directory  
- [x] `railway.json` configuration file created
- [x] `Procfile` created for Railway
- [x] CORS configuration updated for production
- [x] Environment variables template ready

## 🚂 Railway Deployment Steps

### 1. Go to Railway
- Visit [railway.app](https://railway.app)
- Click "Start a New Project"
- Login with GitHub

### 2. Connect Repository
- Choose "Deploy from GitHub repo"
- Select your TrustLens.AI repository
- Railway will auto-detect Python project

### 3. Set Environment Variables
**Required:**
```
ETHERSCAN_API_KEY=your_key_here
ENVIRONMENT=production
FRONTEND_ORIGINS=https://your-netlify-site.netlify.app
```

**Optional:**
```
GEMINI_API_KEY=your_key_here
DEBUG=false
CACHE_TTL=300
REQUEST_TIMEOUT=30
```

### 4. Deploy & Test
- Click Deploy
- Wait for build to complete
- Test health endpoint: `https://your-app.railway.app/health`
- Test API docs: `https://your-app.railway.app/docs`

### 5. Connect Frontend
**Update your Netlify site with:**
```
VITE_API_URL=https://your-app.railway.app
```

## 🎯 Success Indicators

- [ ] Railway build completes successfully
- [ ] Health endpoint returns 200 OK
- [ ] API documentation loads
- [ ] Frontend connects without CORS errors
- [ ] Wallet analysis works end-to-end

## 🔧 If Something Goes Wrong

**Build Fails:**
- Check Railway logs
- Verify requirements.txt has all dependencies
- Ensure Python version compatibility

**App Crashes:**
- Check environment variables are set
- Verify Etherscan API key is valid
- Review application logs in Railway

**CORS Errors:**
- Ensure FRONTEND_ORIGINS includes your Netlify URL
- No trailing slash in URL
- Check browser console for specific errors

## 📞 Ready to Deploy?

All files are prepared! Follow the Railway Deployment Guide for detailed steps.

Your backend will be live in minutes! 🚀