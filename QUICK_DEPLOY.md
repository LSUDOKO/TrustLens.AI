# 🚀 Quick Netlify Deployment Guide

## Step 1: Prepare Your Code
```bash
# Make sure you're in the TrustLens.AI directory
cd TrustLens.AI

# Run the deployment preparation script
./deploy.sh
# or on Windows: bash deploy.sh
```

## Step 2: Deploy to Netlify (Choose one method)

### Method A: Drag & Drop (Easiest)
1. Go to [netlify.com](https://netlify.com) and sign up/login
2. Build your frontend:
   ```bash
   cd frontend
   npm install
   npm run build
   ```
3. Drag the `frontend/dist` folder to Netlify's deploy area
4. Your site will be live instantly!

### Method B: Git Integration (Recommended)
1. Push your code to GitHub:
   ```bash
   git add .
   git commit -m "Add Netlify deployment config"
   git push origin main
   ```
2. Go to [netlify.com](https://netlify.com) → "New site from Git"
3. Connect your repository
4. Use these settings:
   - **Base directory:** `frontend`
   - **Build command:** `npm run build`
   - **Publish directory:** `frontend/dist`
5. Click "Deploy site"

### Method C: Netlify CLI
```bash
# Install Netlify CLI
npm install -g netlify-cli

# Login
netlify login

# Deploy
cd frontend
npm run deploy
```

## Step 3: Configure Environment Variables
In your Netlify dashboard:
1. Go to Site settings → Environment variables
2. Add these variables:
   ```
   NODE_VERSION = 18
   VITE_API_URL = https://your-backend-url.com
   VITE_ENVIRONMENT = production
   ```

## Step 4: Deploy Your Backend
Your frontend needs a backend API. Deploy it to:
- **Railway:** `railway login && railway init && railway up`
- **Render:** Connect your repo at render.com
- **Heroku:** `heroku create && git push heroku main`

## Step 5: Update API URL
After backend deployment:
1. Copy your backend URL
2. Update `VITE_API_URL` in Netlify environment variables
3. Redeploy your site

## 🎉 You're Done!
Your TrustLens.AI app should now be live on Netlify!

## Need Help?
- Check `DEPLOYMENT.md` for detailed instructions
- Netlify docs: [docs.netlify.com](https://docs.netlify.com)
- Issues? Check the troubleshooting section in `DEPLOYMENT.md`