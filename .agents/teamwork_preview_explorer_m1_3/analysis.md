# Test Infrastructure Analysis and AnnotationCanvas Test Design (M1)

This report outlines the recommended testing infrastructure setup for the frontend application using Vitest, jsdom, React Testing Library, and canvas mocking. It also provides a technical blueprint for refactoring the `AnnotationCanvas` component to prevent flickering, ensure clean unmounting, and limit redrawing to user interaction events. Finally, it outlines the unit testing strategies for this ref-based state architecture.

---

## 1. Test Infrastructure Setup

We recommend a lightweight, fast, and ESM-first testing stack that integrates seamlessly with Vite and supports the application's React 19 codebase.

### 1.1 Dependencies to Install
Install the following testing utilities as development dependencies:

```bash
npm install -D vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event vitest-canvas-mock
```

*   **Vitest**: Native ESM test runner built on Vite, reusing existing loaders and config.
*   **jsdom**: Light mock DOM environment to run React rendering tests in Node.
*   **React Testing Library**: For testing components through user interactions. We use the latest version (16.x+) for full React 19 compatibility.
*   **@testing-library/jest-dom**: Offers custom Vitest assertions like `toBeInTheDocument` or `toHaveStyle`.
*   **vitest-canvas-mock**: Mocks the HTML5 Canvas 2D API (`CanvasRenderingContext2D`), tracking method calls so assertions can verify layout drawings without actual screen pixel rendering.

### 1.2 Configuration Files

#### 1.2.1 Vite and Vitest Configuration (`vite.config.ts`)
To configure Vitest, reference the Vitest type definitions and insert the `test` configuration block directly inside the existing `vite.config.ts`. Change the `defineConfig` import from `'vite'` to `'vitest/config'`:

```typescript
/// <reference types="vitest" />
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { defineConfig } from 'vitest/config';

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      hmr: process.env.DISABLE_HMR !== 'true',
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: './src/test/setup.ts',
      css: false, // Turn off CSS processing for faster tests
    },
  };
});
```

#### 1.2.2 TypeScript Configuration (`tsconfig.json`)
Add `vitest/globals` to compiler types in `tsconfig.json` so typescript compiles test files with global variables like `describe`, `it`, `expect`, and `vi` without manual imports:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "experimentalDecorators": true,
    "useDefineForClassFields": false,
    "module": "ESNext",
    "lib": [
      "ES2022",
      "DOM",
      "DOM.Iterable"
    ],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "isolatedModules": true,
    "moduleDetection": "force",
    "allowJs": true,
    "jsx": "react-jsx",
    "paths": {
      "@/*": [
        "./*"
      ]
    },
    "allowImportingTsExtensions": true,
    "noEmit": true,
    "types": [
      "vitest/globals"
    ]
  }
}
```

#### 1.2.3 Global Test Setup File (`src/test/setup.ts`)
Create this setup file to automatically register canvas mocks, include jest-dom matchers, and reset hooks after each test:

```typescript
import '@testing-library/jest-dom/vitest';
import 'vitest-canvas-mock';
import { vi, afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// Reset mock state and clean up React Testing Library trees
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
```

### 1.3 Scripts inside `package.json`
Add the following commands under the `"scripts"` key in `package.json`:

```json
"scripts": {
  "test": "vitest",
  "test:run": "vitest run",
  "test:coverage": "vitest run --coverage",
  "test:ui": "vitest --ui"
}
```

---

## 2. Refactoring `AnnotationCanvas` to a Ref-Based State

### 2.1 The Issue with React State for Canvas Operations
In `src/components/AnnotationCanvas.tsx`, state variables like `scale`, `offset`, `panStart`, `isPanning`, `isDrawing`, `drawStart`, and `drawingBbox` are stored in React state via `useState`. 

When panning or drawing:
1. Panning and dragging generate mousemove events at high frequencies (up to 60+ events per second).
2. Each event calls `setOffset` or `setDrawingBbox`, triggering a React component re-render.
3. React re-render invokes virtual DOM diffing, recreates event handlers, and runs component logic (including the console debug logging).
4. The canvas rendering `useEffect` runs asynchronously *after* the DOM update. This mismatch between event firing, React scheduling, and screen painting leads to visual stutter, lag, and distinct **flickering** (especially if canvas dimensions are recalculated and cause context resets).

### 2.2 Ref-Based Alternative Design
To eliminate lag and flickering, transient zoom/pan/drag data must be stored in React **refs**. Because updating refs does not trigger component renders, we can paint directly to the canvas in sync with events.

#### Transitioning to Refs
1. Replace state declarations with refs:
```typescript
const scaleRef = useRef<number>(1);
const offsetRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
const isPanningRef = useRef<boolean>(false);
const panStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

const isDrawingRef = useRef<boolean>(false);
const drawStartRef = useRef<{ x: number; y: number } | null>(null);
const drawingBboxRef = useRef<[number, number, number, number] | null>(null);
```

2. Create an imperative `redraw` function that reads directly from the refs:
```typescript
const redraw = () => {
  const canvas = canvasRef.current;
  if (!canvas || !image) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  // Clear canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  ctx.save();
  // Apply zoom and pan transformations
  ctx.translate(offsetRef.current.x, offsetRef.current.y);
  ctx.scale(scaleRef.current, scaleRef.current);

  // 1. Draw PDF page document
  ctx.drawImage(image, 0, 0);

  // 2. Draw existing bboxes
  detections.forEach((det, idx) => {
    // ... drawing logic using local `detections` prop ...
  });

  // 3. Draw active drawing bbox
  if (drawingBboxRef.current) {
    const [x0, y0, x1, y1] = drawingBboxRef.current;
    // ... drawing dashed rectangle using refs ...
  }

  ctx.restore();
};
```

3. Frame-lock calls to `redraw` using `requestAnimationFrame`. This debounces multiple mousemove events in a single paint cycle, eliminating stutter:
```typescript
let animationFrameId: number | null = null;

const requestRedraw = () => {
  if (animationFrameId !== null) return;
  animationFrameId = requestAnimationFrame(() => {
    redraw();
    animationFrameId = null;
  });
};
```

### 2.3 Event Listener Setup & Cleanups
Instead of registering event listeners via JSX attributes (which can make capturing and blocking passive events like wheel scrolls difficult in modern browsers), register them imperatively inside a `useEffect`. This ensures cleanups are executed on component unmount to prevent memory leaks:

```typescript
useEffect(() => {
  const canvas = canvasRef.current;
  if (!canvas) return;

  const handleMouseDown = (e: MouseEvent) => {
    if (canvasMode === 'pan') {
      if (e.button === 0 && hoveredDetectionIndex === null) {
        isPanningRef.current = true;
        panStartRef.current = { x: e.clientX, y: e.clientY };
      }
    } else if (canvasMode === 'draw') {
      if (activeModelTab !== 'GT') return;
      if (e.button === 0) {
        const coords = getCanvasCoordsFromClient(e.clientX, e.clientY);
        if (coords) {
          isDrawingRef.current = true;
          drawStartRef.current = coords;
          drawingBboxRef.current = [coords.x, coords.y, coords.x, coords.y];
          requestRedraw();
        }
      }
    }
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (canvasMode === 'pan') {
      if (isPanningRef.current) {
        const dx = e.clientX - panStartRef.current.x;
        const dy = e.clientY - panStartRef.current.y;
        offsetRef.current = {
          x: offsetRef.current.x + dx,
          y: offsetRef.current.y + dy
        };
        panStartRef.current = { x: e.clientX, y: e.clientY };
        requestRedraw();
        return;
      }
      
      // Hover detection logic
      const coords = getCanvasCoordsFromClient(e.clientX, e.clientY);
      if (!coords) return;
      let foundIdx: number | null = null;
      for (let i = detections.length - 1; i >= 0; i--) {
        const [x0, y0, x1, y1] = detections[i].bbox;
        if (coords.x >= x0 && coords.x <= x1 && coords.y >= y0 && coords.y <= y1) {
          foundIdx = i;
          break;
        }
      }
      if (foundIdx !== hoveredDetectionIndex) {
        setHoveredDetectionIndex(foundIdx); // This reacts, triggering effect redraw
      }
    } else if (canvasMode === 'draw') {
      if (isDrawingRef.current && drawStartRef.current) {
        const coords = getCanvasCoordsFromClient(e.clientX, e.clientY);
        if (coords) {
          drawingBboxRef.current = [
            Math.min(drawStartRef.current.x, coords.x),
            Math.min(drawStartRef.current.y, coords.y),
            Math.max(drawStartRef.current.x, coords.x),
            Math.max(drawStartRef.current.y, coords.y)
          ];
          requestRedraw();
        }
      }
    }
  };

  const handleMouseUp = (e: MouseEvent) => {
    if (canvasMode === 'pan') {
      isPanningRef.current = false;
    } else if (canvasMode === 'draw') {
      if (isDrawingRef.current && drawingBboxRef.current) {
        const [x0, y0, x1, y1] = drawingBboxRef.current;
        const w = x1 - x0;
        const h = y1 - y0;
        if (w > 6 && h > 6) {
          addDetection(selectedDrawClass, [x0, y0, x1, y1]);
        }
      }
      isDrawingRef.current = false;
      drawStartRef.current = null;
      drawingBboxRef.current = null;
      requestRedraw();
    }
  };

  const handleMouseLeave = () => {
    isPanningRef.current = false;
    isDrawingRef.current = false;
    drawStartRef.current = null;
    drawingBboxRef.current = null;
    setHoveredDetectionIndex(null);
    requestRedraw();
  };

  const handleWheel = (e: WheelEvent) => {
    e.preventDefault(); // Intercept default page scroll/zoom
    const zoomIntensity = 0.08;
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const imgX = (mouseX - offsetRef.current.x) / scaleRef.current;
    const imgY = (mouseY - offsetRef.current.y) / scaleRef.current;

    const zoomFactor = e.deltaY < 0 ? (1 + zoomIntensity) : (1 - zoomIntensity);
    const nextScale = Math.max(0.12, Math.min(6, scaleRef.current * zoomFactor));

    offsetRef.current = {
      x: mouseX - imgX * nextScale,
      y: mouseY - imgY * nextScale
    };
    scaleRef.current = nextScale;
    requestRedraw();
  };

  canvas.addEventListener('mousedown', handleMouseDown);
  canvas.addEventListener('mousemove', handleMouseMove);
  canvas.addEventListener('mouseup', handleMouseUp);
  canvas.addEventListener('mouseleave', handleMouseLeave);
  canvas.addEventListener('wheel', handleWheel, { passive: false });

  // Initial draw
  redraw();

  return () => {
    canvas.removeEventListener('mousedown', handleMouseDown);
    canvas.removeEventListener('mousemove', handleMouseMove);
    canvas.removeEventListener('mouseup', handleMouseUp);
    canvas.removeEventListener('mouseleave', handleMouseLeave);
    canvas.removeEventListener('wheel', handleWheel);
    if (animationFrameId !== null) {
      cancelAnimationFrame(animationFrameId);
    }
  };
}, [image, detections, canvasMode, selectedDrawClass, hoveredDetectionIndex, activeModelTab]);
```

---

## 3. Testing AnnotationCanvas's Ref-Based State

Because refs do not trigger DOM changes, simply querying rendering outcomes or DOM texts will not suffice to assert coordinate updates. We propose three main verification strategies:

### Strategy 1: Expose Refs via `useImperativeHandle` (Cleanest & Recommended)
Using `React.forwardRef` and `useImperativeHandle`, the component can securely expose getter functions to the testing environment. This allows unit tests to assert directly on numerical values without having to mock pixel-by-pixel canvas drawing.

#### Implementation in component:
```typescript
export interface AnnotationCanvasHandle {
  getScale: () => number;
  getOffset: () => { x: number; y: number };
  getDrawingBbox: () => [number, number, number, number] | null;
}

export const AnnotationCanvas = React.forwardRef<AnnotationCanvasHandle, AnnotationCanvasProps>(
  ({ detections, imagePath }, ref) => {
    const scaleRef = useRef(1);
    const offsetRef = useRef({ x: 0, y: 0 });
    const drawingBboxRef = useRef<[number, number, number, number] | null>(null);

    React.useImperativeHandle(ref, () => ({
      getScale: () => scaleRef.current,
      getOffset: () => offsetRef.current,
      getDrawingBbox: () => drawingBboxRef.current,
    }));
    
    // ... rest of component logic ...
  }
);
```

#### Test implementation (`src/components/AnnotationCanvas.test.tsx`):
```typescript
import { createRef } from 'react';
import { render, fireEvent } from '@testing-library/react';
import { AnnotationCanvas, AnnotationCanvasHandle } from './AnnotationCanvas';
import { vi, describe, it, expect } from 'vitest';

describe('AnnotationCanvas Zooming & Panning Refs', () => {
  it('should update internal scale on mouse wheel zoom-in', () => {
    const canvasRef = createRef<AnnotationCanvasHandle>();
    
    render(<AnnotationCanvas ref={canvasRef} detections={[]} imagePath="dummy.png" />);
    
    const canvas = document.getElementById('clinical_annotation_canvas')!;
    
    // Simulate zooming in
    fireEvent.wheel(canvas, { deltaY: -100, clientX: 300, clientY: 300 });

    expect(canvasRef.current?.getScale()).toBeGreaterThan(1);
    expect(canvasRef.current?.getOffset().x).not.toBe(0);
  });

  it('should update offset coordinates on drag pan gestures', () => {
    const canvasRef = createRef<AnnotationCanvasHandle>();
    
    render(<AnnotationCanvas ref={canvasRef} detections={[]} imagePath="dummy.png" />);
    
    const canvas = document.getElementById('clinical_annotation_canvas')!;
    
    // Panning involves MouseDown -> MouseMove -> MouseUp
    fireEvent.mouseDown(canvas, { button: 0, clientX: 100, clientY: 100 });
    fireEvent.mouseMove(canvas, { clientX: 150, clientY: 120 });
    fireEvent.mouseUp(canvas);

    expect(canvasRef.current?.getOffset()).toEqual({
      x: 50, // clientX delta (150 - 100)
      y: 20  // clientY delta (120 - 100)
    });
  });
});
```

### Strategy 2: Spying on Canvas 2D Transformations (Black-box Context Mocking)
If modifying the component signature with `forwardRef` is not preferred, we can use `vitest-canvas-mock` to verify interactions apply the correct transformation matrix directly to the 2D rendering context.

#### Test implementation:
```typescript
import { render, fireEvent } from '@testing-library/react';
import { AnnotationCanvas } from './AnnotationCanvas';
import { vi, describe, it, expect } from 'vitest';

describe('AnnotationCanvas Canvas Context Calls', () => {
  it('should invoke context translate and scale on panning', () => {
    // Spy on canvas context methods
    const translateSpy = vi.spyOn(CanvasRenderingContext2D.prototype, 'translate');
    const scaleSpy = vi.spyOn(CanvasRenderingContext2D.prototype, 'scale');

    render(<AnnotationCanvas detections={[]} imagePath="dummy.png" />);
    const canvas = document.getElementById('clinical_annotation_canvas')!;

    // Perform panning action
    fireEvent.mouseDown(canvas, { button: 0, clientX: 200, clientY: 200 });
    fireEvent.mouseMove(canvas, { clientX: 250, clientY: 210 });
    fireEvent.mouseUp(canvas);

    expect(translateSpy).toHaveBeenCalled();
    expect(scaleSpy).toHaveBeenCalled();
  });
});
```

### Strategy 3: Verifying Event Listener Cleanup on Unmount
To ensure event listeners are detached and do not leak memory when swapping pages or modes, spy on the underlying element's `addEventListener` and `removeEventListener` methods.

#### Test implementation:
```typescript
import { render } from '@testing-library/react';
import { AnnotationCanvas } from './AnnotationCanvas';
import { vi, describe, it, expect } from 'vitest';

describe('AnnotationCanvas Lifecycle Cleanups', () => {
  it('should clean up all registered event listeners on unmount', () => {
    const addListenerSpy = vi.spyOn(HTMLCanvasElement.prototype, 'addEventListener');
    const removeListenerSpy = vi.spyOn(HTMLCanvasElement.prototype, 'removeEventListener');

    const { unmount } = render(
      <AnnotationCanvas detections={[]} imagePath="dummy.png" />
    );

    // Get count of registered canvas events
    const registrations = addListenerSpy.mock.calls.length;
    expect(registrations).toBeGreaterThan(0);

    // Unmount
    unmount();

    // The count of remove calls must equal the add calls
    expect(removeListenerSpy).toHaveBeenCalledTimes(registrations);
  });
});
```

### Strategy 4: Verifying Rendering Isolation (No React Re-renders)
Test that mouse events and canvas drawing updates do not trigger React re-renders, establishing high-performance, flicker-free isolation.

#### Test implementation:
```typescript
import { useState } from 'react';
import { render, fireEvent } from '@testing-library/react';
import { AnnotationCanvas } from './AnnotationCanvas';
import { vi, describe, it, expect } from 'vitest';

describe('AnnotationCanvas Render Performance', () => {
  it('should not trigger React re-renders during high-frequency panning', () => {
    let renderCount = 0;

    const ComponentWrapper = () => {
      renderCount++;
      return <AnnotationCanvas detections={[]} imagePath="dummy.png" />;
    };

    render(<ComponentWrapper />);
    const canvas = document.getElementById('clinical_annotation_canvas')!;

    expect(renderCount).toBe(1);

    // Perform multiple zoom/pan events
    for (let i = 0; i < 20; i++) {
      fireEvent.mouseDown(canvas, { button: 0, clientX: 100, clientY: 100 });
      fireEvent.mouseMove(canvas, { clientX: 100 + i, clientY: 100 + i });
      fireEvent.mouseUp(canvas);
    }

    // React render count remains 1, proving panning runs entirely in raw canvas memory space
    expect(renderCount).toBe(1);
  });
});
```
