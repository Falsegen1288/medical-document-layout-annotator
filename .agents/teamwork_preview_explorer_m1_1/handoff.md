# Handoff Report

## 1. Observation
- **Project Structure**:
  - React/TypeScript code resides in `src/`.
  - `package.json` specifies `"dependencies": { "react": "^19.0.1", "react-dom": "^19.0.1", "vite": "^6.2.3" }`.
  - No existing test framework files are present in the directory.
- **Component AnnotationCanvas**:
  - Location: `src/components/AnnotationCanvas.tsx`
  - High-frequency interaction state hook declarations:
    - Line 23: `const [scale, setScale] = useState<number>(1);`
    - Line 24: `const [offset, setOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });`
    - Line 25: `const [isPanning, setIsPanning] = useState<boolean>(false);`
    - Line 26: `const [panStart, setPanStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });`
    - Line 29: `const [isDrawing, setIsDrawing] = useState<boolean>(false);`
    - Line 30: `const [drawStart, setDrawStart] = useState<{ x: number; y: number } | null>(null);`
    - Line 31: `const [drawingBbox, setDrawingBbox] = useState<[number, number, number, number] | null>(null);`
  - Render hook:
    - Line 96-170: `useEffect(() => { ... }, [image, detections, scale, offset, hoveredDetectionIndex, resizedDimensions, drawingBbox, selectedDrawClass]);`
    - Line 65: Instantiates `new ResizeObserver(...)` targeting `containerRef.current`.

## 2. Logic Chain
- **Issue with Current Setup**:
  1. Setting React state (e.g. `setOffset`, `setDrawingBbox`) in `mousemove` and `wheel` event handlers triggers React's scheduler for a component re-render.
  2. During high-frequency gestures, React diffs virtual DOM trees and updates element attributes multiple times a frame.
  3. The drawing code is locked inside a React `useEffect` which relies on these state variables as dependencies, creating an async gap between mouse events, state dispatching, React rendering, and direct canvas draw calls.
  4. This asynchronously batched execution creates rendering lag and flickering during drag-to-pan or drag-to-draw gestures.
- **Proposed Solution**:
  1. Replace high-frequency states with React refs (`useRef`). Since updating `ref.current` does not trigger React renders, visual updates can be done immediately.
  2. Implement a synchronous `draw()` method that accesses `ref.current` values directly and draws to the canvas synchronously in response to mouse/wheel event listeners.
  3. To enable `e.preventDefault()` on wheel events (required to inhibit default browser viewport scroll) and ensure memory cleanliness, manually mount raw canvas event listeners inside a `useEffect` and unbind them during cleanup on component unmount.
- **Testing Approach**:
  1. In JSDOM, canvas rendering context isn't fully simulated natively. `vitest-canvas-mock` intercepts canvas calls and turns them into spies (`vi.fn()`), letting tests assert that drawing commands (e.g., `scale()`, `translate()`) are fired.
  2. Exposing the ref states via a private property (`canvas.__testState`) on the canvas element in test environments enables unit tests to inspect the synchronous, unrendered states of refs directly.
  3. Mocking `ResizeObserver` and HTML elements' `clientWidth`/`clientHeight` prevents runtime JSDOM crashes and provides mock sizing values.

## 3. Caveats
- Visual layout changes in parent elements (e.g. resizing browser) will still require updating react state (`resizedDimensions`) to adjust canvas HTML element parameters (`width` and `height`).
- Setting `.src` of an HTML Image element in JSDOM does not natively trigger loading, so we must mock `Image.prototype.src` setter to execute `.onload` synchronously.

## 4. Conclusion
- A high-performance testing and ref-based interaction canvas structure has been fully designed and recommended. This includes:
  - Vitest + jsdom + React Testing Library + `vitest-canvas-mock` configuration.
  - Refactoring plan for `AnnotationCanvas.tsx` using refs instead of states for pan offset, scale, and drag coordinates.
  - A comprehensive testing strategy to verify internal refs (via a test-hook property), canvas draws, and unmount cleanup.

## 5. Verification Method
- **Analysis Verification**: Inspect `.agents/teamwork_preview_explorer_m1_1/analysis.md` to review the proposed setup commands, configurations, code samples, and testing instructions.
- **Test Command**: Once dependencies are installed, testing can be run with `npm run test` or `npx vitest run`.
