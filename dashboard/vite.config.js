import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: './',
  publicDir: '../data', // expose data/current.json at /current.json
  build: {
    outDir: 'dist',
  },
});
