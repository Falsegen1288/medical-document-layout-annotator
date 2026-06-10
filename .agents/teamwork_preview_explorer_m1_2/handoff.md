# Handoff Report — M1 Test Infrastructure Recommendation

## 1. Observation
1. **Existing Scripts and Dependencies**: In `package.json`, there are no test scripts under the `"scripts"` object (lines 6-12) and no test-related libraries under `"dependencies"` or `"devDependencies"` (lines 13-37). Only building, linting, and running scripts are configured:
   ```json
   "scripts": {
     "dev": "vite --host 127.0.0.1 --port 3000",
     "build": "vite build",
     "preview": "vite preview",
     "clean": "rm -rf dist server.js",
     "lint": "tsc --noEmit"
   }
   ```
2. **Canvas State Implementation**: In `src/components/AnnotationCanvas.tsx`, state variables for drawing and panning are stored as React states (lines 23-31):
   ```typescript
   const [scale, setScale] = useState<number>(1);
   const [offset, setOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
   const [isPanning, setIsPanning] = useState<boolean>(false);
   const [panStart, setPanStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
   const [isDrawing, setIsDrawing] = useState<boolean>(false);
   const [drawStart, setDrawStart] = useState<{ x: number; y: number } | null>(null);
   const [drawingBbox, setDrawingBbox] = useState<[number, number, number, number] | null>(null);
   ```
3. **Canvas Element Layout**: In `src/components/AnnotationCanvas.tsx` (lines 347-362), the canvas attributes `width` and `height` are directly bound to the `resizedDimensions` state, which changes when parent size changes:
   ```typescript
   <canvas
     id="clinical_annotation_canvas"
     ref={canvasRef}
     width={resizedDimensions.width}
     height={resizedDimensions.height}
     onMouseMove={handleMouseMove}
     onMouseDown={handleMouseDown}
     onMouseUp={handleMouseUp}
     onMouseLeave={handleMouseLeave}
     onWheel={handleWheel}
     ...
   />
   ```
4. **Debug Logging**: The component contains an active render-cycle console debug log with no dependency array (lines 50-59), causing browser console writes on every render.
5. **No Existing Tests**: No `*.test.ts`, `*.test.tsx`, `*.spec.ts`, or `*.spec.tsx` files exist in the `src/` directory.

---

## 2. Logic Chain
1. Since the project utilizes Vite for bundling and TypeScript for building (Observed in `package.json` and `vite.config.ts`), **Vitest** is the logical choice for a test runner. It natively shares configurations with Vite, runs fast, and avoids bundling overhead during testing.
2. Because React components require a DOM environment to render, and node does not natively provide one, **jsdom** is recommended to mock browser APIs (Observed in standard RTL setups).
3. The component `AnnotationCanvas.tsx` performs layout rendering on an HTML5 `<canvas>` (Observed in lines 347-362). Because `jsdom` does not mock Canvas elements or contexts (`getContext('2d')`), running tests on it throws errors or fails silently. **vitest-canvas-mock** is required to intercept rendering context methods and mock them.
4. Canvas panning and drawing updates `useState` variables in event handlers (Observed in `handleMouseMove` and `handleWheel`). In React, setting state on every high-frequency `mousemove` event triggers repeated rendering. When React re-evaluates the `<canvas>` node, it updates `width` and `height` attributes (Observed in JSX lines 350-351). In browser environments, setting canvas `width`/`height` triggers a buffer reset, discarding previous pixels. Because the redraw `useEffect` runs asynchronously after the DOM update, a visible blank frame occurs, causing the visual flickering.
5. To test high-frequency interactions without flickering, the component states must be moved to React `useRef` and bound via imperative listeners (mousedown, mousemove, mouseup, wheel).
6. Because refs do not trigger re-renders, standard DOM testing queries (like looking for layout changes in HTML elements) won't reflect coordinate updates. Thus:
   * We must dispatch mouse and wheel events to trigger the handlers.
   * We must verify state changes using either black-box spied canvas context methods (e.g., `translate`, `scale`) provided by `vitest-canvas-mock`, or white-box attributes (`data-canvas-scale`, `data-canvas-offset-x`) updated imperatively inside the drawing loop.
   * We must spy on `addEventListener` and `removeEventListener` of the canvas to verify listener registration and unmount cleanups.

---

## 3. Caveats
* The analysis assumes that `@testing-library/react` and `vitest-canvas-mock` are compatible with React 19. Using `@testing-library/react` v16+ is necessary to properly support React 19's rendering cycle.
* Canvas mocking via `vitest-canvas-mock` is a virtual context mock; it does not verify visual layout pixels directly (for pixel-level visual regression, visual regression testing tools like Playwright/Cypress are needed, which are outside of the unit-testing scope of M1).

---

## 4. Conclusion
We recommend establishing an M1 test infrastructure utilizing **Vitest**, **jsdom**, **React Testing Library**, and **vitest-canvas-mock**. The scripts, `vitest.config.ts`, and `vitest.setup.ts` configurations are detailed in `analysis.md`.
To address visual flickering and support robust testing, the `AnnotationCanvas` must be refactored to use refs (`useRef`) and imperative event listeners. Tests should simulate events, inspect spied context draw calls, verify unmount cleanup of listeners, and assert values via custom debugging attributes on the canvas DOM element.

---

## 5. Verification Method
1. **Inspect Report**: Read and inspect `analysis.md` located at `.agents/teamwork_preview_explorer_m1_2/analysis.md` to review the proposed configurations, scripts, refactoring logic, and the complete sample test file.
2. **Setup Integration**: Once the packages are installed, verify the setup by running:
   ```bash
   npm run test
   ```
   or running individual tests using Vitest's CLI.
3. **Mock Validation**: Inspect the mock logs in the console to ensure that mock elements (e.g. `ResizeObserver`, `URL.createObjectURL`) are registered without throwing errors.
