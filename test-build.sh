#!/bin/bash

# Test build script for TrustLens.AI
echo "🧪 Testing TrustLens.AI build locally..."

cd frontend

# Clean everything
echo "🧹 Cleaning previous builds..."
rm -rf node_modules package-lock.json dist

# Set Node version (if using nvm)
if command -v nvm &> /dev/null; then
    echo "📦 Using Node.js version from .nvmrc..."
    nvm use
fi

# Install dependencies
echo "📥 Installing dependencies..."
npm install --legacy-peer-deps

# Build the project
echo "🔨 Building project..."
npm run build

if [ $? -eq 0 ]; then
    echo "✅ Build test completed successfully!"
    echo "📁 Build output is in the 'dist' directory"
    echo "🌐 You can test it locally with: npm run preview"
else
    echo "❌ Build test failed!"
    exit 1
fi