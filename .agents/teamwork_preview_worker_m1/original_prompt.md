## 2026-06-10T08:03:47Z

Your task is to set up the test infrastructure (M1) for the React + TS project:
1. Install development dependencies:
   npm install -D vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event vitest-canvas-mock @types/react @types/react-dom
2. Modify package.json to include:
   "test": "vitest",
   "test:run": "vitest run",
   "test:coverage": "vitest run --coverage"
3. Create a vitest.config.ts in the project root:
   import { defineConfig, mergeConfig } from 'vitest/config';
   import viteConfigFunc from './vite.config';
   export default defineConfig((env) => {
     const baseConfig = typeof viteConfigFunc === 'function' ? viteConfigFunc(env) : viteConfigFunc;
     return mergeConfig(
       baseConfig,
       {
         test: {
           globals: true,
           environment: 'jsdom',
           setupFiles: ['./vitest.setup.ts'],
           include: ['src/**/*.{test,spec}.{ts,tsx}'],
         },
       }
     );
   });
4. Create a vitest.setup.ts in the project root:
   import '@testing-library/jest-dom';
   import 'vitest-canvas-mock';
   import { vi, afterEach } from 'vitest';
   import { cleanup } from '@testing-library/react';
   afterEach(() => {
     cleanup();
     vi.clearAllMocks();
   });
   // Mock ResizeObserver
   class ResizeObserverMock {
     observe = vi.fn();
     unobserve = vi.fn();
     disconnect = vi.fn();
   }
   window.ResizeObserver = ResizeObserverMock as any;
   // Mock URL APIs
   if (typeof window !== 'undefined') {
     window.URL.createObjectURL = vi.fn(() => 'blob:mock-image-url');
     window.URL.revokeObjectURL = vi.fn();
   }
5. Run the test command to verify the setup runs (it will say no tests found or similar).
Document your installation, command outputs, and verify layout compliance in c:\Users\user\Downloads\medical-document-layout-annotator\.agents\teamwork_preview_worker_m1\handoff.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
