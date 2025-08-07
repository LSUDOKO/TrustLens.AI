# 🔧 Netlify Deployment Troubleshooting

## Issues: Build Errors on Netlify

### Issue 1: `crypto.hash is not a function`
This error occurs due to Node.js version compatibility issues with Vite 7.x.

### Issue 2: `npm ci` package-lock sync errors
This happens when dependencies are added but package-lock.json isn't updated.

### Issue 3: Engine compatibility warnings
React Router 7 and Vite 7 require Node.js 20+.

Here are the solutions:

### ✅ Solution 1: Updated Configuration (Applied)

I've updated your configuration with these fixes:

1. **Node.js Version**: Changed to Node 20 for compatibility with Vite 7 and React Router 7
2. **Vite Config**: Updated build target and minifier
3. **Package.json**: Added terser dependency
4. **Build Command**: Uses `npm install` instead of `npm ci` to handle lock file sync
5. **Package Lock**: Removed outdated package-lock.json to force regeneration

### 🚀 Quick Fix Commands

If the build still fails, try these steps:

```bash
# 1. Clean everything
cd frontend
rm -rf node_modules package-lock.json dist

# 2. Reinstall with legacy peer deps
npm install --legacy-peer-deps

# 3. Test build locally
npm run build

# 4. If successful, commit and push
git add .
git commit -m "Fix Netlify build configuration"
git push
```

### 🔄 Alternative Netlify Settings

If the current config doesn't work, try these build settings in Netlify dashboard:

**Build Settings:**
- **Base directory:** `frontend`
- **Build command:** `rm -f package-lock.json && npm install --legacy-peer-deps && npm run build`
- **Publish directory:** `frontend/dist`

**Environment Variables:**
```
NODE_VERSION=20
NODE_OPTIONS=--max-old-space-size=4096
NODE_ENV=production
NPM_CONFIG_PRODUCTION=false
```

### 🛠️ Manual Build Test

Test the build locally before deploying:

```bash
cd frontend

# Install dependencies
npm ci --legacy-peer-deps

# Build the project
npm run build

# Preview the build
npm run preview
```

### 🔍 Common Issues & Solutions

#### Issue: "Module not found" errors
**Solution:** Clear node_modules and reinstall
```bash
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps
```

#### Issue: "Out of memory" errors
**Solution:** Increase Node.js memory limit
```bash
export NODE_OPTIONS="--max-old-space-size=4096"
npm run build
```

#### Issue: Vite version conflicts
**Solution:** Use specific Vite version
```bash
npm install vite@^5.0.0 --save-dev
```

### 📋 Netlify Deploy Checklist

- [ ] Node.js version set to 18
- [ ] Build command includes `--legacy-peer-deps`
- [ ] Publish directory is `frontend/dist` (not `dist`)
- [ ] Environment variables are set correctly
- [ ] Local build works successfully

### 🆘 If All Else Fails

1. **Downgrade Vite:**
   ```bash
   npm install vite@^5.4.0 --save-dev
   ```

2. **Use Simple Build:**
   Update `netlify.toml`:
   ```toml
   [build]
     base = "frontend/"
     publish = "dist/"
     command = "npm install && npm run build"
   ```

3. **Manual Deploy:**
   ```bash
   cd frontend
   npm run build
   # Then drag the dist folder to Netlify
   ```

### 📞 Need More Help?

- Check Netlify build logs for specific error messages
- Try deploying a simple HTML file first to test basic setup
- Consider using Netlify CLI for more control: `netlify deploy --dir=dist`

The configuration has been updated to fix the crypto.hash error. Try redeploying now!