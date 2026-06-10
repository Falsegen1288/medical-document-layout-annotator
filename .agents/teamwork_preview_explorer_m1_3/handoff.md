# Handoff Report — Test Infrastructure & AnnotationCanvas Test Design (M1)

## 1. Observation
- `package.json` lines 6-12 do not specify any test command, and lines 26-37 show no testing-related packages under `devDependencies`.
- `vite.config.ts` lines 6-22 configure plugins and dev servers but do not define a `test` object or configure Vitest.
- `src/components/AnnotationCanvas.tsx` lines 23-31 define the panning, zoom, and drawing states using standard React state hooks:
  ```typescript
  // Zoom and Pan States
  const [scale, setScale] = useState<number>(1);
  const [offset, setOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState<boolean>(false);
  const [panStart, setPanStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Drawing States
  const [isDrawing, setIsDrawing] = useState<boolean>(false);
  const [drawStart, setDrawStart] = useState<{ x: number; y: number } | null>(null);
  const [drawingBbox, setDrawingBbox] = useState<[number, number, number, number] | null>(null);
  ```
- `src/components/AnnotationCanvas.tsx` lines 96-170 use a standard `useEffect` to redraw on the canvas context whenever these state variables change:
  ```typescript
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !image) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    // ... drawing operations ...
  }, [image, detections, scale, offset, hoveredDetectionIndex, resizedDimensions, drawingBbox, selectedDrawClass]);
  ```
- React 19 is listed under `package.json` line 21: `"react": "^19.0.1"`.

## 2. Logic Chain
- High-frequency events (like mouse drag and mouse wheel scrolling) trigger updates to zoom/pan/drag state values multiple times per frame.
- Since these values are React component state variables, updating them triggers a synchronous component re-render on every update, causing high CPU/GPU usage, layout shifts, and visual **flickering** during rapid movement.
- To resolve this:
  - Transitioning these values to React `useRef` instances prevents component re-renders during high-frequency mouse actions.
  - Canvas updates can then be executed synchronously or frame-locked using `requestAnimationFrame(redraw)` directly inside event handlers.
  - Event listeners must be registered inside `useEffect` on mounting and removed on unmount to prevent listener leakages.
- For testing these ref-based components (where standard React Testing Library DOM text queries cannot observe state changes):
  - Spying on the 2D rendering context transformations using `vitest-canvas-mock` will verify if translation and scaling are applied correctly on interaction.
  - Exposing getter functions using `React.forwardRef` and `useImperativeHandle` permits clean, unit-test level assertions directly against ref values without mocking canvas operations.
  - Spying on canvas `addEventListener` and `removeEventListener` asserts lifecycle cleanup.
  - Spying on component render counts verifies that zoom, pan, and drag operations run in complete isolation from the React render loop.

## 3. Caveats
- No active code refactoring has been performed because the task is restricted to a read-only investigation.
- Verification commands (like `npm test`) are not yet runnable inside the repository since the packages have not been installed.

## 4. Conclusion
- A high-performance, flicker-free canvas setup is achievable by refactoring zoom/pan/drag coordinate tracking to React `useRef` objects and manually triggering frame-locked draw calls.
- The proposed M1 testing infrastructure (Vitest + jsdom + RTL + vitest-canvas-mock) fully supports this setup through clean unit tests, canvas method spying, and listener cleanups.

## 5. Verification Method
- **Inspection**: Open and read the analysis report in `c:\Users\user\Downloads\medical-document-layout-annotator\.agents\teamwork_preview_explorer_m1_3\analysis.md`.
- **Validation**: Confirm the report contains all four core parts: package installation commands, configurations for Vite and TypeScript, ref-based refactoring sketch, and concrete test cases for canvas spying, ref testing, cleanup, and render isolation.
