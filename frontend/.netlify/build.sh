#!/bin/bash

# Netlify build script for TrustLens.AI
echo "🌐 Starting Netlify build for TrustLens.AI..."

# Set environment variables
export NODE_ENV=production
export NODE_OPTIONS="--max-old-space-size=4096"

# Clear npm cache to avoid issues
npm cache clean --force

# Install dependencies
echo "📦 Installing dependencies..."
npm ci

# Build the project
echo "🔨 Building project..."
npm run build

echo "✅ Netlify build completed!"