import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        app: resolve(__dirname, 'app.html'),
      },
    },
    // Use more compatible build settings
    target: 'es2020',
    minify: 'terser',
    sourcemap: false,
    // Increase chunk size limit
    chunkSizeWarningLimit: 1000,
  },
  // Server configuration for development
  server: {
    port: 5173,
    host: true,
  },
  // Preview configuration
  preview: {
    port: 4173,
    host: true,
  },
});
