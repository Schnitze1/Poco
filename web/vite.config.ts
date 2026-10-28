import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  // Relative base so assets work on GitHub Pages project sites
  // (https://user.github.io/REPO/) and locally.
  base: './',
  plugins: [react()],
  test: {
    environment: 'jsdom',
    coverage: {
      provider: 'v8',
      // Include unimported application files so the baseline reflects the whole app.
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.test.{ts,tsx}', 'src/**/*.d.ts'],
      reporter: ['text', 'html', 'json-summary', 'lcov'],
      reportsDirectory: 'coverage',
      reportOnFailure: true,
      thresholds: { lines: 80 },
    },
  },
})
