# TrustLens.AI Deployment Guide

This guide will help you deploy TrustLens.AI to Netlify (frontend) and other platforms (backend).

## 🚀 Frontend Deployment to Netlify

### Option 1: Deploy via Netlify Dashboard (Recommended)

1. **Prepare your repository:**

   ```bash
   git add .
   git commit -m "Add Netlify deployment configuration"
   git push origin main
   ```

2. **Connect to Netlify:**

   - Go to [netlify.com](https://netlify.com) and sign up/login
   - Click "New site from Git"
   - Connect your GitHub/GitLab/Bitbucket account
   - Select your TrustLens.AI repository

3. **Configure build settings:**

   - **Base directory:** `frontend`
   - **Build command:** `npm run build`
   - **Publish directory:** `frontend/dist`
   - **Node version:** `18` (set in Environment variables)

4. **Set environment variables:**
   Go to Site settings > Environment variables and add:

   ```
   NODE_VERSION=18
   VITE_API_URL=https://your-backend-url.com
   VITE_ENVIRONMENT=production
   ```

5. **Deploy:**
   - Click "Deploy site"
   - Netlify will automatically build and deploy your site
   - You'll get a URL like `https://amazing-name-123456.netlify.app`

### Option 2: Deploy via Netlify CLI

1. **Install Netlify CLI:**

   ```bash
   npm install -g netlify-cli
   ```

2. **Login to Netlify:**

   ```bash
   netlify login
   ```

3. **Build and deploy:**
   ```bash
   cd frontend
   npm install
   npm run build
   netlify deploy --prod --dir=dist
   ```

## 🔧 Backend Deployment Options

Since Netlify is for static sites, you'll need to deploy your FastAPI backend separately.

### Option 1: Railway (Recommended)

1. **Install Railway CLI:**

   ```bash
   npm install -g @railway/cli
   ```

2. **Deploy:**

   ```bash
   railway login
   railway init
   railway up
   ```

3. **Set environment variables:**
   ```bash
   railway variables set ETHERSCAN_API_KEY=your_etherscan_key
   railway variables set GEMINI_API_KEY=your_gemini_key
   railway variables set ENVIRONMENT=production
   ```

### Option 2: Render

1. Create a `render.yaml` in your project root:

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
   ```

2. Connect your repository to Render and deploy

### Option 3: Heroku

1. **Create Procfile:**

   ```
   web: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

2. **Deploy:**
   ```bash
   heroku create your-app-name
   heroku config:set ETHERSCAN_API_KEY=your_key
   heroku config:set GEMINI_API_KEY=your_key
   git push heroku main
   ```

## 🔗 Connecting Frontend to Backend

After deploying your backend, update your frontend environment variables:

1. **In Netlify dashboard:**

   - Go to Site settings > Environment variables
   - Update `VITE_API_URL` to your backend URL
   - Redeploy the site

2. **Or in your local `.env` file:**
   ```
   VITE_API_URL=https://your-backend-url.com
   ```

## 🛠️ Environment Variables Reference

### Frontend (.env)

```
VITE_API_URL=https://your-backend-url.com
VITE_ENVIRONMENT=production
```

### Backend (.env)

```
ETHERSCAN_API_KEY=your_etherscan_api_key
GEMINI_API_KEY=your_gemini_api_key
ENVIRONMENT=production
DEBUG=false
FRONTEND_ORIGINS=https://your-netlify-site.netlify.app
REDIS_URL=redis://your-redis-url:6379
```

## 🔍 Troubleshooting

### Common Issues:

1. **Build fails with "crypto.hash is not a function":**

   - This is a Node.js/Vite compatibility issue
   - Solution: Use Node.js 18 and `--legacy-peer-deps` flag
   - See `NETLIFY_TROUBLESHOOTING.md` for detailed fixes

2. **Build fails on Netlify:**

   - Check Node.js version (should be 18)
   - Use build command: `npm ci --legacy-peer-deps && npm run build`
   - Ensure publish directory is `frontend/dist`

3. **API calls fail:**

   - Verify VITE_API_URL is correct
   - Check CORS settings in backend
   - Ensure backend is deployed and accessible

4. **Environment variables not working:**
   - Prefix frontend variables with `VITE_`
   - Restart/redeploy after changing variables
   - Check variable names for typos

### Useful Commands:

```bash
# Test local build
cd frontend && npm run build && npm run preview

# Check Netlify deployment status
netlify status

# View Netlify logs
netlify logs

# Test backend health
curl https://your-backend-url.com/health
```

## 🚀 Custom Domain (Optional)

1. **In Netlify dashboard:**

   - Go to Site settings > Domain management
   - Click "Add custom domain"
   - Follow DNS configuration instructions

2. **SSL Certificate:**
   - Netlify provides free SSL certificates
   - Will be automatically configured for custom domains

## 📊 Monitoring

- **Netlify Analytics:** Built-in analytics for your site
- **Backend Monitoring:** Use your hosting platform's monitoring tools
- **Health Checks:** Monitor `/health` endpoint for backend status

Your TrustLens.AI application should now be successfully deployed! 🎉
