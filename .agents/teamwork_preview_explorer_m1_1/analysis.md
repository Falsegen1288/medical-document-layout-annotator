# Analysis and Recommendation: M1 Test Infrastructure & Canvas Optimization

## 1. Executive Summary
This report provides a complete design and strategy for the Milestone 1 (M1) Test Infrastructure setup and the optimization of the `AnnotationCanvas` component.
1. **Test Infrastructure**: Setup Vitest, jsdom, React Testing Library, and `vitest-canvas-mock` for high-performance frontend testing in React 19.
2. **Ref-Based Canvas Rendering**: Propose a design to refactor high-frequency state variables (scale, offset, panning/drawing states) from React `useState` to React `useRef`. This completely eliminates React component re-render loops on every pixel of mouse movements or scroll wheels, removing all rendering lag and flickering.
3. **Synchronous Direct Canvas Rendering**: Trigger drawings directly and synchronously in canvas event handlers, bound to native canvas elements with robust unmount cleanup.
4. **Comprehensive Test Plan & Code**: Showcase how to test these ref-based states and verify canvas updates, image loading, zoom/pan events, drawing bounding boxes, and event listener cleanup in jsdom.

---

## 2. Test Infrastructure Setup (M1)

### 2.1 Dependencies Installation
To support test execution using Vitest, jsdom, and React Testing Library (RTL) inside a React 19 codebase, the following packages should be added to `package.json` under `devDependencies`:

```bash
npm install -D vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event vitest-canvas-mock
```

- **`vitest`**: A modern, blazing fast unit-testing framework integrated with Vite.
- **`jsdom`**: Simulates a web browser environment in Node.js.
- **`@testing-library/react`**: Provides utilities to render React components and interact with them in tests.
- **`@testing-library/jest-dom`**: Custom Jest/Vitest matchers to assert on DOM states.
- **`vitest-canvas-mock`**: Mocks the canvas `2D` and `WebGL` contexts, replacing context operations with spies.

### 2.2 Configuration Files

#### `vitest.config.ts`
Create a standalone configuration file in the project root directory:

```typescript
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
        setupFiles: ['./src/setupTests.ts'],
        include: ['src/**/*.test.{ts,tsx}', 'src/**/*.spec.{ts,tsx}'],
        deps: {
          optimizer: {
            web: {
              include: ['vitest-canvas-mock'],
            },
          },
        },
      },
    }
  );
});
```

#### `src/setupTests.ts`
Create the setup file to configure globals, DOM matchers, and mocks:

```typescript
import '@testing-library/jest-dom';
import 'vitest-canvas-mock';

// 1. Mock ResizeObserver so component sizing logic doesn't crash in jsdom
class ResizeObserverMock {
  callback: (entries: any[]) => void;
  constructor(callback: (entries: any[]) => void) {
    this.callback = callback;
  }
  observe(target: HTMLElement) {
    // Instantly trigger callback to simulate layout container dimension setup
    this.callback([
      {
        contentRect: {
          width: target.clientWidth || 800,
          height: target.clientHeight || 650,
        },
      },
    ]);
  }
  unobserve = vi.fn();
  disconnect = vi.fn();
}
global.ResizeObserver = ResizeObserverMock;

// 2. Mock clientWidth/clientHeight on HTMLElement prototype for container dimension calculations
Object.defineProperty(HTMLElement.prototype, 'clientWidth', {
  configurable: true,
  get() {
    return this.id === 'canvas_container_panel' ? 800 : 0;
  },
});

Object.defineProperty(HTMLElement.prototype, 'clientHeight', {
  configurable: true,
  get() {
    return this.id === 'canvas_container_panel' ? 650 : 0;
  },
});
```

### 2.3 Package Scripts
Update `package.json` with standard testing scripts:

```json
"scripts": {
  "test": "vitest run",
  "test:watch": "vitest",
  "test:coverage": "vitest run --coverage"
}
```

---

## 3. Refactoring AnnotationCanvas to Ref-Based States

### 3.1 Problem Analysis: Why Current State Causes Flickering
Currently, `AnnotationCanvas` stores interaction values using React state hooks (`useState`):
- `scale`, `offset` (zoom/pan offset)
- `isPanning`, `panStart`
- `isDrawing`, `drawStart`, `drawingBbox` (box drawing coordinates)

**How it degrades performance and causes flickering:**
1. **Frequent Re-renders**: A pan drag or box draw operation fires dozens of `mousemove` events per second. Each event triggers React state setters. React schedules a component re-render, diffs the virtual DOM, re-instantiates variables, and mounts/remounts child nodes.
2. **Batching Latency**: React updates states asynchronously. In a high-frequency drag, the rendering of the drawing on the canvas lags behind the mouse pointer.
3. **Canvas Clear-Draw Decoupling**: In `AnnotationCanvas.tsx`, drawing is done inside a `useEffect` hooked to the state dependencies. If a browser resize or React re-render resets the `<canvas width={...} height={...}>` element parameters, the canvas is cleared immediately. The `useEffect` drawing runs shortly after in a separate macro-task/micro-task, causing the canvas to flash/flicker blank.

### 3.2 Solution: React `useRef` for Animation States
By converting interaction variables into React `useRef` instances, we bypass the React render cycle completely during drags and zooms.

```typescript
// Replace useState with useRef for interaction states
const scaleRef = useRef<number>(1);
const offsetRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
const isPanningRef = useRef<boolean>(false);
const panStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

const isDrawingRef = useRef<boolean>(false);
const drawStartRef = useRef<{ x: number; y: number } | null>(null);
const drawingBboxRef = useRef<[number, number, number, number] | null>(null);
```

#### What stays in React state?
Only states that directly govern UI markup layout (buttons, dropdowns, overlays) should remain:
- `canvasMode` ('pan' | 'draw')
- `selectedDrawClass` (active annotation class)
- `loading` and `image` (controls loading spinner mount)
- `resizedDimensions` (canvas HTML element size updates)

### 3.3 Synchronous Direct Canvas Drawing
We define a synchronous `draw()` function. Whenever a mouse or wheel event updates a ref value, we immediately call `draw()`.

```typescript
const draw = () => {
  const canvas = canvasRef.current;
  if (!canvas || !image) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  // Clear previous canvas state
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  ctx.save();
  // Apply scale/translate transformations using the current ref values
  ctx.translate(offsetRef.current.x, offsetRef.current.y);
  ctx.scale(scaleRef.current, scaleRef.current);

  // 1. Draw PDF Page Image
  ctx.drawImage(image, 0, 0);

  // 2. Draw Detections
  detections.forEach((det, idx) => {
    const [x0, y0, x1, y1] = det.bbox;
    const color = CLASS_COLORS[det.type] || '#46f1c5';
    const isHovered = hoveredDetectionIndex === idx;

    ctx.fillStyle = hexToRgba(color, isHovered ? 0.35 : 0.15);
    ctx.fillRect(x0, y0, x1 - x0, y1 - y0);

    ctx.lineWidth = isHovered ? 3 : 1.5;
    ctx.strokeStyle = color;
    ctx.strokeRect(x0, y0, x1 - x0, y1 - y0);
    // ... Text drawing logic ...
  });

  // 3. Draw Active Temporary Box
  if (drawingBboxRef.current) {
    const [x0, y0, x1, y1] = drawingBboxRef.current;
    const drawColor = CLASS_COLORS[selectedDrawClass];
    ctx.fillStyle = hexToRgba(drawColor, 0.25);
    ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
    ctx.lineWidth = 2;
    ctx.strokeStyle = drawColor;
    ctx.setLineDash([6, 4]);
    ctx.strokeRect(x0, y0, x1 - x0, y1 - y0);
    ctx.setLineDash([]);
  }

  ctx.restore();
};
```

To sync changes to reactive variables (like when `detections` change or the `image` loads), we trigger `draw()` via `useEffect`:
```typescript
useEffect(() => {
  draw();
}, [image, detections, hoveredDetectionIndex, resizedDimensions, selectedDrawClass]);
```

### 3.4 Raw Event Listeners and Unmount Cleanups
To support non-passive scrolling inhibition (`e.preventDefault()` inside wheel events) and guarantee cleanup, we hook up native event listeners:

```typescript
useEffect(() => {
  const canvas = canvasRef.current;
  if (!canvas) return;

  const handleMouseMoveRaw = (e: MouseEvent) => {
    // Update refs (scaleRef, offsetRef, drawingBboxRef) and call draw() synchronously
    if (canvasMode === 'pan') {
      if (isPanningRef.current) {
        const dx = e.clientX - panStartRef.current.x;
        const dy = e.clientY - panStartRef.current.y;
        offsetRef.current = { x: offsetRef.current.x + dx, y: offsetRef.current.y + dy };
        panStartRef.current = { x: e.clientX, y: e.clientY };
        draw();
        return;
      }
      // Hover detection check...
    } else if (canvasMode === 'draw' && isDrawingRef.current && drawStartRef.current) {
      const currentCoords = getCanvasCoords(e);
      if (currentCoords) {
        drawingBboxRef.current = [
          Math.min(drawStartRef.current.x, currentCoords.x),
          Math.min(drawStartRef.current.y, currentCoords.y),
          Math.max(drawStartRef.current.x, currentCoords.x),
          Math.max(drawStartRef.current.y, currentCoords.y)
        ];
        draw();
      }
    }
  };

  const handleMouseDownRaw = (e: MouseEvent) => {
    if (canvasMode === 'pan') {
      if (e.button === 0) {
        isPanningRef.current = true;
        panStartRef.current = { x: e.clientX, y: e.clientY };
      }
    } else if (canvasMode === 'draw' && e.button === 0) {
      const coords = getCanvasCoords(e);
      if (coords) {
        isDrawingRef.current = true;
        drawStartRef.current = coords;
        drawingBboxRef.current = [coords.x, coords.y, coords.x, coords.y];
        draw();
      }
    }
  };

  const handleMouseUpRaw = (e: MouseEvent) => {
    if (canvasMode === 'pan') {
      isPanningRef.current = false;
    } else if (canvasMode === 'draw') {
      if (isDrawingRef.current && drawingBboxRef.current) {
        const [x0, y0, x1, y1] = drawingBboxRef.current;
        if (x1 - x0 > 6 && y1 - y0 > 6) {
          addDetection(selectedDrawClass, [x0, y0, x1, y1]);
        }
      }
      isDrawingRef.current = false;
      drawStartRef.current = null;
      drawingBboxRef.current = null;
      draw();
    }
  };

  const handleMouseLeaveRaw = () => {
    isPanningRef.current = false;
    isDrawingRef.current = false;
    drawStartRef.current = null;
    drawingBboxRef.current = null;
    draw();
  };

  const handleWheelRaw = (e: WheelEvent) => {
    e.preventDefault(); // Inhibit page scroll
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
    draw();
  };

  // Bind Listeners
  canvas.addEventListener('mousemove', handleMouseMoveRaw);
  canvas.addEventListener('mousedown', handleMouseDownRaw);
  canvas.addEventListener('mouseup', handleMouseUpRaw);
  canvas.addEventListener('mouseleave', handleMouseLeaveRaw);
  canvas.addEventListener('wheel', handleWheelRaw, { passive: false });

  // Cleanup on unmount or mode toggle
  return () => {
    canvas.removeEventListener('mousemove', handleMouseMoveRaw);
    canvas.removeEventListener('mousedown', handleMouseDownRaw);
    canvas.removeEventListener('mouseup', handleMouseUpRaw);
    canvas.removeEventListener('mouseleave', handleMouseLeaveRaw);
    canvas.removeEventListener('wheel', handleWheelRaw);
  };
}, [canvasMode, selectedDrawClass, image, detections]);
```

---

## 4. Testing Strategy for Ref-Based States

Because ref updates (`scaleRef.current`, etc.) do not trigger React re-renders, standard DOM testing queries (like looking for updated inner texts) won't suffice. We recommend a three-fold testing strategy:

### 4.1 Exposing Internal Ref-States to Tests (Test-Hook Pattern)
To inspect the current values of internal refs in unit tests without changing the visual interface, assign a private `__testState` property to the Canvas DOM node during rendering under test environments:

```typescript
// Inside AnnotationCanvas.tsx
if (process.env.NODE_ENV === 'test' && canvasRef.current) {
  (canvasRef.current as any).__testState = {
    scale: scaleRef.current,
    offset: offsetRef.current,
    drawingBbox: drawingBboxRef.current,
    isDrawing: isDrawingRef.current,
    isPanning: isPanningRef.current
  };
}
```
In our tests, we query the canvas node and inspect `canvas.__testState` directly:
```typescript
const canvas = screen.getByTestId('clinical-annotation-canvas');
expect(canvas.__testState.scale).toBe(1.0);
```

### 4.2 Mocking Global Image Loading
Since `AnnotationCanvas` initializes an `Image` object and waits for the `onload` event to finish loading, we mock `Image` in our test code to trigger loading synchronously with specific canvas sizing:

```typescript
beforeAll(() => {
  Object.defineProperty(global.Image.prototype, 'src', {
    set(src) {
      this.width = 1000;
      this.height = 800;
      setTimeout(() => {
        if (this.onload) this.onload();
      }, 0);
    },
  });
});
```

### 4.3 Verifying Canvas Context Drawings via `vitest-canvas-mock`
`vitest-canvas-mock` turns all context methods into spies (`vi.fn()`). This allows tests to verify actual drawing instructions issued to the canvas:
```typescript
const ctx = canvas.getContext('2d');
// Verify zoom scale transformation was applied
expect(ctx.scale).toHaveBeenCalledWith(expect.any(Number), expect.any(Number));
// Verify PDF page drawing was executed
expect(ctx.drawImage).toHaveBeenCalled();
```

---

## 5. Concrete Test Code Example

Here is a complete, ready-to-use unit test spec `AnnotationCanvas.test.tsx` illustrating all of the above strategies:

```typescript
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, beforeAll } from 'vitest';
import { AnnotationCanvas } from './AnnotationCanvas';
import { AnnotationProvider } from '../context/AnnotationContext';

// Mock the context methods
const mockAddDetection = vi.fn();
const mockSetHoveredDetectionIndex = vi.fn();

vi.mock('../context/AnnotationContext', () => ({
  useAnnotation: () => ({
    hoveredDetectionIndex: null,
    setHoveredDetectionIndex: mockSetHoveredDetectionIndex,
    addDetection: mockAddDetection,
    activeModelTab: 'GT',
  }),
}));

describe('AnnotationCanvas Component', () => {
  const mockDetections = [
    { type: 'text' as const, bbox: [100, 150, 300, 250] as [number, number, number, number], model: 'human' }
  ];

  beforeAll(() => {
    // Mock image loader in JSDOM
    Object.defineProperty(global.Image.prototype, 'src', {
      set(src) {
        this.width = 1000;
        this.height = 800;
        setTimeout(() => {
          if (this.onload) this.onload();
        }, 10);
      },
    });
  });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading overlay initially, and mounts canvas after image loads', async () => {
    render(<AnnotationCanvas detections={mockDetections} imagePath="/test-image.jpg" />);
    
    // Check for loading indicator
    expect(screen.getByText(/LOADING SOURCE DOCUMENT IMAGES/i)).toBeInTheDocument();

    // Wait for the simulated image load to fire onload
    await waitFor(() => {
      expect(screen.queryByText(/LOADING SOURCE DOCUMENT IMAGES/i)).not.toBeInTheDocument();
    });

    const canvas = document.getElementById('clinical_annotation_canvas');
    expect(canvas).toBeInTheDocument();
  });

  it('correctly tracks panning offset refs on drag mouse-move', async () => {
    render(<AnnotationCanvas detections={mockDetections} imagePath="/test-image.jpg" />);

    await waitFor(() => {
      expect(screen.queryByText(/LOADING SOURCE DOCUMENT IMAGES/i)).not.toBeInTheDocument();
    });

    const canvas = document.getElementById('clinical_annotation_canvas') as any;

    // Simulate drag start
    fireEvent.mouseDown(canvas, { button: 0, clientX: 100, clientY: 100 });
    expect(canvas.__testState.isPanning).toBe(true);

    // Simulate drag movement
    fireEvent.mouseMove(canvas, { clientX: 150, clientY: 120 });
    
    // Verify offsets shifted by delta: dx=50, dy=20
    expect(canvas.__testState.offset.x).toBeGreaterThan(0);
    expect(canvas.__testState.offset).toEqual({ x: 50, y: 20 });

    // Drag release
    fireEvent.mouseUp(canvas);
    expect(canvas.__testState.isPanning).toBe(false);
  });

  it('correctly updates scale ref on wheel events', async () => {
    render(<AnnotationCanvas detections={mockDetections} imagePath="/test-image.jpg" />);

    await waitFor(() => {
      expect(screen.queryByText(/LOADING SOURCE DOCUMENT IMAGES/i)).not.toBeInTheDocument();
    });

    const canvas = document.getElementById('clinical_annotation_canvas') as any;

    const initialScale = canvas.__testState.scale;

    // Simulate wheel event zoom in (deltaY negative)
    fireEvent.wheel(canvas, { deltaY: -120, clientX: 400, clientY: 300 });

    expect(canvas.__testState.scale).toBeGreaterThan(initialScale);
  });

  it('cleans up event listeners completely on component unmount', async () => {
    const { unmount } = render(<AnnotationCanvas detections={mockDetections} imagePath="/test-image.jpg" />);

    await waitFor(() => {
      expect(screen.queryByText(/LOADING SOURCE DOCUMENT IMAGES/i)).not.toBeInTheDocument();
    });

    const canvas = document.getElementById('clinical_annotation_canvas')!;
    
    const addSpy = vi.spyOn(canvas, 'addEventListener');
    const removeSpy = vi.spyOn(canvas, 'removeEventListener');

    unmount();

    // Verify all active canvas-bound listeners were cleaned up
    expect(removeSpy).toHaveBeenCalledWith('mousemove', expect.any(Function));
    expect(removeSpy).toHaveBeenCalledWith('mousedown', expect.any(Function));
    expect(removeSpy).toHaveBeenCalledWith('mouseup', expect.any(Function));
    expect(removeSpy).toHaveBeenCalledWith('mouseleave', expect.any(Function));
    expect(removeSpy).toHaveBeenCalledWith('wheel', expect.any(Function));
  });
});
```
