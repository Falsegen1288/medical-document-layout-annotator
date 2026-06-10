# Test Infrastructure Recommendation & Canvas Testing Strategy (M1)

## Executive Summary
This report presents a complete test infrastructure recommendation (M1) for the `medical-document-layout-annotator` project. It covers the installation, configuration, and integration of **Vitest**, **jsdom**, **React Testing Library**, and **vitest-canvas-mock**.

Furthermore, it details a robust design pattern to refactor the interactive `AnnotationCanvas` component into a **ref-based, event-driven, non-flickering canvas architecture** and provides specific strategies and a complete unit test implementation template to verify:
1. High-frequency interactions (scale, pan offset, drag coordinates) without triggering React re-renders.
2. Proper cleanup of DOM event listeners and `requestAnimationFrame` hooks on unmount to prevent memory leaks.
3. Decoupling of the render loop from React state updates, ensuring canvas redraws occur only on relevant events.

---

## 1. M1 Test Infrastructure Architecture

To implement a modern, high-performance testing environment that aligns with the Vite build tool and React 19, we recommend the following stack:

| Technology | Purpose | Key Benefits |
|---|---|---|
| **Vitest** | Test runner | Blazing fast, native ESM support, matches Vite configuration, out-of-the-box support for TypeScript and HMR. |
| **jsdom** | Browser environment simulation | Runs in Node.js, providing virtual implementations of DOM APIs (document, window) so React components can render. |
| **React Testing Library (RTL)** | React component testing | Promotes behavior-driven testing by interacting with the DOM similarly to how a user would. Fully compatible with React 19. |
| **vitest-canvas-mock** | Canvas API polyfill and mocks | HTML5 Canvas is not implemented in jsdom. This package intercepts canvas context calls and replaces them with spied mocks, preventing runtime errors and enabling context drawing assertions. |

---

## 2. Installation Plan & package.json Scripts

### Dependency Packages
Run the following command to install the testing dependencies under `devDependencies`:
```bash
npm install -D vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event vitest-canvas-mock @types/react @types/react-dom
```

### package.json Scripts
Add these test scripts to the `"scripts"` field in `package.json` to support local interactive testing, CI verification, and coverage analysis:

```json
"scripts": {
  "dev": "vite --host 127.0.0.1 --port 3000",
  "build": "vite build",
  "preview": "vite preview",
  "clean": "rm -rf dist server.js",
  "lint": "tsc --noEmit",
  "test": "vitest",
  "test:run": "vitest run",
  "test:coverage": "vitest run --coverage"
}
```

---

## 3. Configuration Setup

### A. Vitest Configuration (`vitest.config.ts`)
Create a dedicated `vitest.config.ts` in the project root. This extends the existing `vite.config.ts` options using Vitest's `mergeConfig` utility to ensure environment settings are shared (like aliases and plugins) while keeping the test configurations organized.

```typescript
// vitest.config.ts
import { defineConfig, mergeConfig } from 'vitest/config';
import viteConfig from './vite.config';

export default mergeConfig(
  viteConfig({ command: 'serve', mode: 'development' }),
  defineConfig({
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['./vitest.setup.ts'],
      include: ['src/**/*.{test,spec}.{ts,tsx}'],
      css: true,
    },
  })
);
```

### B. Setup File (`vitest.setup.ts`)
Create a setup file to import Jest DOM matchers, register the canvas mock, and define custom mocks for standard APIs that are missing or stubbed in jsdom (e.g. `ResizeObserver` and `URL.createObjectURL`).

```typescript
// vitest.setup.ts
import '@testing-library/jest-dom';
import 'vitest-canvas-mock';
import { vi } from 'vitest';

// Mock ResizeObserver which is used in AnnotationCanvas but not supported by jsdom
class ResizeObserverMock {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
window.ResizeObserver = ResizeObserverMock as any;

// Mock URL APIs since they are used for object URLs in image handling
if (typeof window !== 'undefined') {
  window.URL.createObjectURL = vi.fn(() => 'blob:mock-image-url');
  window.URL.revokeObjectURL = vi.fn();
}
```

---

## 4. Refactoring `AnnotationCanvas` to a Ref-Based Architecture

### The Problem in the Current Code (Flickering & Slowdowns)
In `src/components/AnnotationCanvas.tsx` (Lines 23–31), canvas states like `scale`, `offset`, `isPanning`, `isDrawing`, and `drawingBbox` are stored in React states (`useState`).
*   During mouse movement (panning/drawing), `mousemove` events fire up to 120 times per second.
*   Each event calls React state updates (e.g., `setOffset`), causing the component to re-evaluate.
*   Because the `<canvas>` element's `width` and `height` attributes in JSX are bound to the `resizedDimensions` state, React's DOM reconciliation modifies these attributes during rendering, which automatically clears the canvas back-buffer.
*   This clear occurs before the `useEffect` draw hook runs, showing a white/blank canvas periodically and causing visual flickering.
*   Additionally, re-binding JSX handlers (`onMouseMove={handleMouseMove}`) continuously on every render causes event-listener churn.

### The Ref-Based Solution
1.  **Ref States**: Store high-frequency interaction variables in `useRef` to avoid triggering React renders:
    ```typescript
    const scaleRef = useRef<number>(1);
    const offsetRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
    const isPanningRef = useRef<boolean>(false);
    const panStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
    const isDrawingRef = useRef<boolean>(false);
    const drawStartRef = useRef<{ x: number; y: number } | null>(null);
    const drawingBboxRef = useRef<[number, number, number, number] | null>(null);
    const canvasModeRef = useRef<'pan' | 'draw'>('pan');
    ```
2.  **Imperative Event Handlers**: Attach event listeners directly in a `useEffect` and clean them up on unmount.
3.  **Unified Draw Loop with requestAnimationFrame**: Draw synchronously inside handlers or schedule a redraw using `requestAnimationFrame` (rAF) to synchronize with monitor refresh cycles.
4.  **Decouple Canvas Dimensions**: Set `canvas.width` and `canvas.height` only when actual resizing occurs (inside the `ResizeObserver` callback), rather than setting them in JSX on every state render.

---

## 5. Strategies for Testing Ref-Based Canvas Components

Since refs do not trigger React state changes or re-renders, standard DOM-based test assertions (e.g., querying elements by text or style) are not applicable. We recommend the following five testing strategies:

### Strategy 1: Simulating High-Frequency Mouse & Wheel Events
Use `@testing-library/react`'s `fireEvent` (or `dispatchEvent`) to send mouse coordinates, mouse down/up states, and scroll deltas directly to the canvas element.
*   **Panning**: Dispatch `mousedown` -> `mousemove` with deltas -> `mouseup`.
*   **Drawing**: Toggle Mode -> Dispatch `mousedown` -> `mousemove` -> `mouseup`.
*   **Zooming**: Dispatch a `wheel` event with `deltaY`.

### Strategy 2: Black-Box Context Spy Assertions
Since `vitest-canvas-mock` intercepts canvas rendering, the 2D context (`canvas.getContext('2d')`) is fully mocked. We can spy on calls like `.translate()`, `.scale()`, `.fillRect()`, and `.drawImage()`.
*   Assert that dragging the mouse in Pan mode triggers `ctx.translate(dx, dy)`.
*   Assert that zooming in triggers `ctx.scale(s, s)`.
*   Assert that drawing in Draw mode triggers `ctx.strokeRect(...)` or `ctx.fillRect(...)`.

### Strategy 3: White-Box Debug Attributes (Highly Recommended)
To prevent tests from relying entirely on fragile drawing command coordinates, have the `drawCanvas` function write the internal ref values (scale, offsets) to custom DOM data-attributes on the canvas:
```typescript
const drawCanvas = () => {
  const canvas = canvasRef.current;
  if (!canvas) return;
  // Draw operations...
  canvas.setAttribute('data-canvas-scale', scaleRef.current.toString());
  canvas.setAttribute('data-canvas-offset-x', offsetRef.current.x.toString());
  canvas.setAttribute('data-canvas-offset-y', offsetRef.current.y.toString());
};
```
In tests, we can verify the state by querying:
```typescript
expect(canvas).toHaveAttribute('data-canvas-scale', '1.15');
```
This is elegant, does not trigger React renders, and makes assertions highly readable and robust.

### Strategy 4: Verifying Event Listener Cleanups
To ensure event listeners are removed on unmount:
1.  Spy on `HTMLCanvasElement.prototype.addEventListener` and `HTMLCanvasElement.prototype.removeEventListener`.
2.  Render the component and record the number of listeners added.
3.  Unmount the component.
4.  Verify that all added listeners were removed (i.e. `removeEventListener` calls match the `addEventListener` signatures).

### Strategy 5: Verifying Drawing Loop Performance (No Re-renders / No Flicker)
To verify redrawing without flickering:
*   Mock `requestAnimationFrame` and `cancelAnimationFrame` in the test.
*   Ensure that high-frequency events (like `mousemove`) cause `requestAnimationFrame` scheduling, but **do not** increment the component render counts (which can be tracked by a local count variable or a console log spy).

---

## 6. Sample Test Implementation

Here is a complete, ready-to-use unit test file (`src/components/AnnotationCanvas.test.tsx`) demonstrating all five strategies:

```typescript
// src/components/AnnotationCanvas.test.tsx
import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { AnnotationCanvas } from './AnnotationCanvas';
import { useAnnotation } from '../context/AnnotationContext';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';

// Mock the context hook
vi.mock('../context/AnnotationContext', () => ({
  useAnnotation: vi.fn(),
}));

describe('AnnotationCanvas (Ref-Based Architecture)', () => {
  const mockDetections = [
    { id: '1', bbox: [10, 10, 50, 50] as [number, number, number, number], type: 'text' as const },
  ];
  const mockImagePath = 'test-document.jpg';
  let mockAddDetection: any;
  let mockSetHoveredDetectionIndex: any;

  beforeEach(() => {
    mockAddDetection = vi.fn();
    mockSetHoveredDetectionIndex = vi.fn();
    (useAnnotation as any).mockReturnValue({
      hoveredDetectionIndex: null,
      setHoveredDetectionIndex: mockSetHoveredDetectionIndex,
      addDetection: mockAddDetection,
      activeModelTab: 'GT',
    });

    // Mock Image object loading
    vi.spyOn(global, 'Image').mockImplementation(() => {
      const img = {} as HTMLImageElement;
      setTimeout(() => {
        if (img.onload) img.onload({} as Event);
      }, 0);
      return img;
    });

    // Mock requestAnimationFrame for synchronous clock control
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => {
      cb(0);
      return 1;
    });
    vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const renderCanvasComponent = async () => {
    let result: any;
    await act(async () => {
      result = render(<AnnotationCanvas detections={mockDetections} imagePath={mockImagePath} />);
    });
    // Wait for image loading mock to resolve and load state
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 10));
    });
    return result;
  };

  it('renders canvas element after loading image', async () => {
    await renderCanvasComponent();
    const canvas = screen.getByRole('img'); // standard role for canvas with label or specific id query
    expect(canvas).toBeInTheDocument();
  });

  it('should support Pan and Zoom states using refs and custom attributes without triggering React re-renders', async () => {
    // Spy on console.log or tracking function to monitor re-renders
    const renderSpy = vi.spyOn(console, 'group'); 
    
    await renderCanvasComponent();
    const canvas = screen.getByRole('img') as HTMLCanvasElement;
    
    // Clear initial mount render groups
    renderSpy.mockClear();

    // 1. Simulate mouse drag (Panning)
    fireEvent.mouseDown(canvas, { button: 0, clientX: 100, clientY: 100 });
    fireEvent.mouseMove(canvas, { clientX: 150, clientY: 120 });
    fireEvent.mouseUp(canvas);

    // Verify coordinate translation shifts (State assertions via Data-Attributes)
    expect(canvas.getAttribute('data-canvas-offset-x')).toBe('50');
    expect(canvas.getAttribute('data-canvas-offset-y')).toBe('20');

    // Verify Canvas Context 2D methods were called for redraw
    const ctx = canvas.getContext('2d');
    expect(ctx?.translate).toHaveBeenCalled();
    expect(ctx?.drawImage).toHaveBeenCalled();

    // Assert that React component DID NOT re-render (console group logs remains at 0)
    expect(renderSpy).not.toHaveBeenCalled();
  });

  it('should support zooming via scroll wheel event and update refs scale state', async () => {
    await renderCanvasComponent();
    const canvas = screen.getByRole('img') as HTMLCanvasElement;

    // Simulate Wheel Zoom In
    fireEvent.wheel(canvas, { deltaY: -100, clientX: 100, clientY: 100 });

    const scaleAfter = parseFloat(canvas.getAttribute('data-canvas-scale') || '1');
    expect(scaleAfter).toBeGreaterThan(1); // Scale should zoom in
  });

  it('should switch to Draw Mode and fire addDetection when drawing drag is completed', async () => {
    const { container } = await renderCanvasComponent();
    const canvas = screen.getByRole('img') as HTMLCanvasElement;

    // 1. Switch to Draw Mode
    const drawModeBtn = container.querySelector('#draw_mode_toggle_btn');
    expect(drawModeBtn).toBeInTheDocument();
    fireEvent.click(drawModeBtn!);

    // 2. Perform bounding box drag (from 50, 50 to 200, 200)
    fireEvent.mouseDown(canvas, { button: 0, clientX: 50, clientY: 50 });
    fireEvent.mouseMove(canvas, { clientX: 200, clientY: 200 });
    fireEvent.mouseUp(canvas);

    // Verify drawing data-attribute states
    expect(canvas.getAttribute('data-canvas-is-drawing')).toBe('false');

    // Verify global context callback triggers detection inclusion
    expect(mockAddDetection).toHaveBeenCalledWith('text', expect.any(Array));
  });

  it('should clean up all attached event listeners on component unmount to prevent memory leaks', async () => {
    const addListenerSpy = vi.spyOn(HTMLCanvasElement.prototype, 'addEventListener');
    const removeListenerSpy = vi.spyOn(HTMLCanvasElement.prototype, 'removeEventListener');

    const { unmount } = await renderCanvasComponent();

    // Track calls during mount
    const addedEvents = addListenerSpy.mock.calls.map(c => c[0]);
    expect(addedEvents).toContain('mousedown');
    expect(addedEvents).toContain('mousemove');
    expect(addedEvents).toContain('mouseup');
    expect(addedEvents).toContain('wheel');

    // Perform component unmount
    unmount();

    // Track calls during unmount and verify cleanups
    const removedEvents = removeListenerSpy.mock.calls.map(c => c[0]);
    expect(removedEvents).toContain('mousedown');
    expect(removedEvents).toContain('mousemove');
    expect(removedEvents).toContain('mouseup');
    expect(removedEvents).toContain('wheel');

    expect(removedEvents.length).toBeGreaterThanOrEqual(addedEvents.length);
  });
});
```

---

## 7. Performance & Structural Benefits Summary

Adopting this test infrastructure setup and refactoring strategy delivers key visual, architectural, and testability benefits:

1.  **Flicker Elimination**: Standardizing the setting of `canvas.width` / `canvas.height` only on actual resize, rather than on every state redraw, keeps the graphics buffer stable and flicker-free.
2.  **60FPS Panning and Zooming**: Ref-based interactions run independently of React's state queues and schedules, preventing lags and allowing smooth `requestAnimationFrame` drawing.
3.  **Low Test Maintenance**: Data-attributes on the canvas expose internal state updates natively to the test environment, removing the need to write fragile mock context assertions that break with visual styling updates.
4.  **Leak Prevention**: Automated event listener lifecycle verification tests guarantee all DOM bindings are removed on component disposal, ensuring client memory stability.
