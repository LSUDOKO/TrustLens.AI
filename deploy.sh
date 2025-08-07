#!/bin/bash

# TrustLens.AI Deployment Script
echo "🚀 Starting TrustLens.AI deployment..."

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: Please run this script from the TrustLens.AI root directory"
    exit 1
fi

# Frontend deployment
echo "📦 Building frontend..."
cd frontend

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📥 Installing frontend dependencies..."
    npm install
fi

# Build the frontend
echo "🔨 Building frontend for production..."
npm run build

if [ $? -ne 0 ]; then
    echo "❌ Frontend build failed!"
    exit 1
fi

echo "✅ Frontend build completed successfully!"

# Check if Netlify CLI is installed
if command -v netlify &> /dev/null; then
    echo "🌐 Netlify CLI found. You can now deploy with:"
    echo "   netlify deploy --prod --dir=dist"
    echo ""
    echo "Or run: npm run deploy"
else
    echo "⚠️  Netlify CLI not found. Install it with:"
    echo "   npm install -g netlify-cli"
    echo "   netlify login"
    echo "   netlify deploy --prod --dir=dist"
fi

cd ..

echo ""
echo "🎉 Deployment preparation complete!"
echo ""
echo "Next steps:"
echo "1. Deploy frontend to Netlify (see commands above)"
echo "2. Deploy backend to Railway/Render/Heroku (see DEPLOYMENT.md)"
echo "3. Update VITE_API_URL in Netlify environment variables"
echo ""
echo "📖 For detailed instructions, see DEPLOYMENT.md"