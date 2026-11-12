import { defineConfig } from '@playwright/test';
export default defineConfig({
    testDir: './e2e',
    testMatch: process.env.MUNC_E2E_REAL_API ? ['**/live.spec.js', '**/registration-live.spec.js', '**/review-live.spec.js'] : '**/admin.spec.js',
    timeout: 45000,
    workers: 1,
    use: { baseURL: 'http://127.0.0.1:4173', headless: true,
        launchOptions: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH } : {},
        trace: 'retain-on-failure', screenshot: 'only-on-failure' },
    webServer: { command: 'npm run dev -- --host 127.0.0.1 --port 4173 --strictPort',
        url: 'http://127.0.0.1:4173', reuseExistingServer: false,
        env: { VITE_API_BASE_URL: process.env.MUNC_E2E_REAL_API || '/api' } },
});
