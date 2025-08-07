#!/bin/bash

# Netlify build script for TrustLens.AI
echo "🌐 Starting Netlify build for TrustLens.AI..."

# Set environment variables
export NODE_ENV=production
export NODE_OPTIONS="--max-old-space-size=4096"

# Clear npm cache to avoid issues
npm cache clean --force

# Remove existing lock file if it exists (to avoid sync issues)
if [ -f "package-lock.json" ]; then
    echo "🗑️ Removing outdated package-lock.json..."
    rm package-lock.json
fi

# Install dependencies with legacy peer deps
echo "📦 Installing dependencies..."
npm install --legacy-peer-deps

# Build the project
echo "🔨 Building project..."
npm run build

echo "✅ Netlify build completed!"