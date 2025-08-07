#!/bin/bash

# TrustLens.AI Frontend Build Script
echo "🚀 Building TrustLens.AI Frontend..."

# Set Node.js version
export NODE_VERSION=20

# Clear any existing build artifacts
echo "🧹 Cleaning previous builds..."
rm -rf dist/
rm -rf node_modules/.vite/

# Install dependencies with clean cache
echo "📦 Installing dependencies..."
npm ci --prefer-offline --no-audit

# Build the project
echo "🔨 Building for production..."
npm run build

if [ $? -eq 0 ]; then
    echo "✅ Build completed successfully!"
    echo "📁 Build output is in the 'dist' directory"
else
    echo "❌ Build failed!"
    exit 1
fi