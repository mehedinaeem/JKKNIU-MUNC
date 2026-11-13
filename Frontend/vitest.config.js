import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
export default defineConfig({ define: { 'import.meta.env.VITE_API_BASE_URL': JSON.stringify('/api') }, plugins: [react()], test: { environment: 'jsdom', setupFiles: './src/test/setup.js', include: ['src/**/*.test.{js,jsx}'] } });
