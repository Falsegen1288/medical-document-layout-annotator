# Handoff Report - explorer_1

This report documents the read-only investigation of the React annotation canvas in the `medical-document-layout-annotator` workspace.

## 1. Observation
I investigated the workspace filesystem and code structure, confirming the locations and behaviors of the canvas components, states, event handlers, and drawing configurations.

*   **React Components**:
    *   Root mounting point: `src/main.tsx` (Lines 6–10) wraps `<App />` in React `<StrictMode>`.
    *   Application shell: `src/App.tsx` (Lines 25–201) handles tab navigation between pages.
    *   Dataset editing workspace: `src/pages/Annotate.tsx` (Lines 26–554) imports `AnnotationCanvas`.
    *   Interactive canvas component: `src/components/AnnotationCanvas.tsx` (Lines 11–453).
    *   Side-by-side read-only benchmark dashboard: `src/pages/Compare.tsx` (Lines 13–352).
    *   Metrics dashboard and export panels: `src/pages/Export.tsx` (Lines 20–448).
    *   Calculated diagnostic reports: `src/components/EvaluationModal.tsx` (Lines 15–638).
*   **State Management**:
    *   Zustand store: `src/store/annotationStore.ts` (Lines 64–568) defines the core state system.
    *   React Context layer: `src/context/AnnotationContext.tsx` (Lines 34–68) forwards the entire Zustand store object to context:
        ```typescript
        const store = useAnnotationStore();
        const contextValue: AnnotationContextType = { ...store };
        ```
*   **Canvas Drawing**:
    *   `src/components/AnnotationCanvas.tsx` (Lines 96–170) implements canvas painting inside a `useEffect` hook. It clears the canvas area:
        ```typescript
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ```
        Then it transforms, scales, and draws the background document image along with layout annotation boxes.
*   **Flickering & Rendering Bug**:
    *   `src/components/AnnotationCanvas.tsx` (Lines 347–362) sets HTML DOM properties `width` and `height` dynamically using React state values:
        ```typescript
        width={resizedDimensions.width}
        height={resizedDimensions.height}
        ```
    *   Lines 50–59 contains a render-loop debug logger with no dependency array:
        ```typescript
        useEffect(() => {
          console.group('AnnotationCanvas render debug');
          // ... console group logs ...
          console.groupEnd();
        });
        ```
*   **Zoom Behavior**:
    *   `src/components/AnnotationCanvas.tsx` (Lines 281–299) uses only the direction of `deltaY` to determine zoom:
        ```typescript
        const zoomFactor = e.deltaY < 0 ? (1 + zoomIntensity) : (1 - zoomIntensity);
        ```
*   **Project Config & Testing Suite**:
    *   `package.json` specifies Vite (`v6.2.3`), React (`v19.0.1`), Zustand (`v5.0.14`), and TailwindCSS (`v4.1.14`).
    *   There is no testing framework configured in `package.json` (no jest, vitest, or testing-library dependencies are present under `dependencies` or `devDependencies`). There are no test scripts in `package.json` (only `"dev"`, `"build"`, `"preview"`, `"clean"`, and `"lint"` are listed under `"scripts"`).

---

## 2. Logic Chain
1.  **Why the canvas flickers and vibrates**:
    *   The browser automatically clears the graphics context of an HTML5 `<canvas>` whenever its `width` or `height` attributes are modified or re-set, even if set to the identical values.
    *   By binding `width` and `height` properties in the React JSX tag to React state `resizedDimensions.width`/`height` (which gets re-evaluated and synchronized on every component render), the browser clears the backing store on every render.
    *   Because drawing occurs asynchronously within a `useEffect` hook *after* the DOM reconciles, a visible blank frame is left on the screen, creating severe flickering.
    *   This is compounded by the high-frequency state updates fired on every single mouse drag event, the global context refresh that triggers a canvas re-render on any store value update, and the thread-blocking `console.group` log that runs on every render.
2.  **Why zooming is hypersensitive**:
    *   The `zoomFactor` calculations map any trackpad scroll (even tiny deltas) to a full 8% step because the magnitude of `e.deltaY` is completely discarded.
3.  **Why refactoring can be done without writing code**:
    *   We can document a strategy utilizing a rendering reference object (`useRef`) to bypass React state updates for fast mouse dragging events, normalization of `deltaY` to handle trackpad speeds, and direct Zustand slice hook subscriptions.

---

## 3. Caveats
*   **Backend Interactions**: The FastAPI backend server (`http://127.0.0.1:8000`) was not running during this investigation. Integrations like SSE and save routes were verified by analyzing client-side calls in `annotationStore.ts` but were not run live.
*   **Assumptions**: We assume the canvas size should adapt to parent element dimensions via `ResizeObserver` checks.

---

## 4. Conclusion
The visual flickering on the canvas is caused by setting `width` and `height` properties on the JSX element in a high-frequency React render loop, which forces the browser to discard the canvas buffer before it redraws. 

The zoom hypersensitivity is caused by ignoring the magnitude of `e.deltaY`. 

The project has no testing framework. 

All issues can be resolved using the refactoring strategy described in `analysis.md` (which recommends using a mutable `useRef` coordinate store with `requestAnimationFrame`, direct Zustand slice selection, and logarithmic deltaY scaling).

---

## 5. Verification Method
*   **Static Type Check**: To verify type safety of project compilation after any refactoring:
    `npm run lint` (runs `tsc --noEmit`)
*   **Files to Inspect**:
    *   Confirm canvas JSX attributes inside `src/components/AnnotationCanvas.tsx` lines 347–362.
    *   Confirm zoom handler logic in `src/components/AnnotationCanvas.tsx` lines 281–299.
    *   Confirm context subscription in `src/context/AnnotationContext.tsx` lines 34–35.
    *   Confirm dependencies in `package.json`.
*   **Visual Verification**: Run the app locally (`npm run dev`) and test zoom/pan interactions to ensure zero flickering.
