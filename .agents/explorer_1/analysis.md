# Annotation Canvas Investigation & Refactoring Analysis

## Executive Summary
This report analyzes the React annotation canvas implementation in the `medical-document-layout-annotator` project. The application is a layout verification and curation tool for medical document images. The core canvas component suffers from severe visual flickering/vibration during panning or drawing, and has an overly sensitive zoom control on trackpads/modern mouse wheels. 

We identify the root cause of these issues—specifically the repeated clearing of the canvas buffer caused by React re-evaluating DOM elements on every state update, the context subscription anti-pattern, and wheel event scale normalization omission. We present a detailed overview of the system structure and a concrete refactoring strategy.

---

## 1. Codebase Architecture & Components
The application is structured as a client-side React single-page application built on Vite. Below is the mapping of React components and pages.

### Core React Components
*   **Root Wrapper (`App` Component)**
    *   **File Path**: `src/App.tsx` (Lines 203–209)
    *   **Description**: Wraps the application shell in `AnnotationProvider` to supply the global context.
*   **Shell Layout (`MainAppShell` Component)**
    *   **File Path**: `src/App.tsx` (Lines 25–201)
    *   **Description**: Manages tab switching between pages (Dashboard, Dataset, Validation, Metrics) and contains the side-panel document tree list.
*   **Dashboard Page (`Dashboard` Component)**
    *   **File Path**: `src/pages/Dashboard.tsx` (Lines 26–585)
    *   **Description**: Handles PDF file upload drag-and-drop, page range selection, and displays the FastAPI backend extraction pipeline status.
*   **Annotator Workspace (`Annotate` Page Component)**
    *   **File Path**: `src/pages/Annotate.tsx` (Lines 26–554)
    *   **Description**: Houses the main layout workspace, legend panel, list inspector, base model initializations, and instantiates the `AnnotationCanvas`.
*   **Interactive Canvas (`AnnotationCanvas` Component)**
    *   **File Path**: `src/components/AnnotationCanvas.tsx` (Lines 11–453)
    *   **Description**: Performs image and layout bounding box rendering on an HTML5 canvas. Manages tool state modes (Pan/Zoom vs. Draw), scaling, offsets, mouse interactions, and scroll wheel zooming.
*   **Layout Comparison (`Compare` Page Component)**
    *   **File Path**: `src/pages/Compare.tsx` (Lines 13–352)
    *   **Description**: Provides a side-by-side read-only comparison viewport of predictions from Model A (DocLayoutYOLO), Model B (Nemotron), and Model C (ADE-DPT2). *Note: Unlike `Annotate.tsx`, this component renders boxes statically via absolute CSS positioning percentages rather than HTML5 canvas drawing.*
*   **Evaluation Metrics (`EvaluationModal` Component)**
    *   **File Path**: `src/components/EvaluationModal.tsx` (Lines 15–638)
    *   **Description**: Runs layout overlap and sequence metrics (IoU, COTe spatial density, LED structural errors, Reading Order Kendall's Tau) on the fly and renders diagnostic tables.

---

## 2. State Management & Interaction Handlers

### Global State Management
Global state is managed via **Zustand** inside `src/store/annotationStore.ts` (Lines 64–568). The interface `AnnotationState` (Lines 12–60) holds:
*   Uploaded session data (`sessionId`, `pages`, `currentPageIndex`).
*   Active annotation layer/tab configuration (`activeModelTab` = `'ADE' | 'DL' | 'NM' | 'GT'`).
*   Detections currently being edited (`workingDetections`).
*   Interaction targets (`hoveredDetectionIndex`).
*   Actions like `changePage`, `initWorkingDetections`, `updateDetection`, `deleteDetection`, `addDetection`, `confirmPage`.

### Context Wrapper Subscription Anti-Pattern
A React Context wrapper is defined in `src/context/AnnotationContext.tsx` (Lines 34–68):
```typescript
export const AnnotationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const store = useAnnotationStore();
  const contextValue: AnnotationContextType = { ...store };
  return (
    <AnnotationContext.Provider value={contextValue}>
      {children}
    </AnnotationContext.Provider>
  );
};
```
Whenever *any* slice of state in the Zustand store changes (e.g., upload percentages, log strings, undo alerts, page switches), the `AnnotationProvider` re-renders. This instantiates a brand new `contextValue` object. Any component consuming `useAnnotation()` (including `AnnotationCanvas`) is immediately forced to re-render, even if the specific keys it consumes did not change. This bypasses Zustand's built-in selector optimizations.

### Local Component States in `AnnotationCanvas.tsx`
*   `canvasMode` (Line 19) — Current active mouse tool: `'pan'` or `'draw'`.
*   `scale` (Line 23) — Zoom scale factor (default: fit bounds).
*   `offset` (Line 24) — Visual translation offsets `x` and `y`.
*   `isPanning`/`panStart` (Lines 25–26) — Drag tracking for pan tool.
*   `isDrawing`/`drawStart`/`drawingBbox` (Lines 29–31) — Crosshair drawing shape tracking.
*   `resizedDimensions` (Line 62) — Dimensions tracked via `ResizeObserver` to resize canvas.

---

## 3. Canvas Rendering & Coordinate Systems

### Image & Annotation Rendering Flow
1.  **Asynchronous Image Loading** (Lines 34–47): A `useEffect` hook triggers on `imagePath` changes. It loads the source page image (`img.src = imagePath`) into an HTML `Image` object and sets the local state `image`.
2.  **Coordinate Mapping** (Lines 179–189): Canvas mouse operations use client coordinates `e.clientX` / `rect.left`. Coordinates are converted into the document image pixel space (e.g. 1275x1650 original coordinates) by subtracting translation `offset` and dividing by `scale`:
    ```typescript
    const imgX = (x - offset.x) / scale;
    const imgY = (y - offset.y) / scale;
    ```
3.  **Canvas Draw Cycle** (Lines 96–170): An draw `useEffect` hook triggers on changes to `[image, detections, scale, offset, hoveredDetectionIndex, resizedDimensions, drawingBbox, selectedDrawClass]`.
    *   Clears context: `ctx.clearRect(0, 0, canvas.width, canvas.height)`.
    *   Transforms: `ctx.translate(offset.x, offset.y)` followed by `ctx.scale(scale, scale)`.
    *   Draws image: `ctx.drawImage(image, 0, 0)`.
    *   Draws list of annotations: Renders layout category boxes using coordinates stored in `detections` (or `workingDetections` in parent) alongside font label tags.
    *   Draws temporary crosshair drag rectangle: `drawingBbox` (dashed outline).

### Mouse Event Interaction Handlers
*   `handleMouseDown` (Lines 231–251): Begins tracking coordinates. If pan mode, sets `isPanning = true`. If draw mode, sets `isDrawing = true` and initializes `drawStart`.
*   `handleMouseMove` (Lines 191–229):
    *   *Pan Mode*: If `isPanning` is active, calculates mouse translation offsets `dx/dy`, adds them to the current offset, and updates `offset` state. If not panning, checks if the coordinates are inside any bounding box to set `hoveredDetectionIndex`.
    *   *Draw Mode*: If `isDrawing` is active, calculates dragging coordinates and updates the `drawingBbox` state.
*   `handleMouseUp` (Lines 253–271): Releases mouse locks. If drawing a box, ensures dimensions exceed a threshold of `w > 6 && h > 6` image coordinates and fires `addDetection(selectedDrawClass, bbox)`.
*   `handleMouseLeave` (Lines 273–280): Resets locks and clears drag overlays.

---

## 4. Flickering and Vibration Diagnosis
Visual flickering during continuous mouse movement (panning/drawing) is caused by the following chain of interactions:

1.  **Canvas Back Buffer Resetting on React Render**:
    The `<canvas>` JSX element is declared with attributes hooked directly to local states:
    ```typescript
    <canvas
      width={resizedDimensions.width}
      height={resizedDimensions.height}
      ...
    />
    ```
    Every time React re-renders `AnnotationCanvas`, it reconciles the virtual DOM node and updates the DOM attributes `width` and `height`. 
    In HTML5, setting the `width` or `height` properties of a canvas DOM node—**even to their existing values**—instantly clears the graphics context, discarding the current drawing buffer.
    Because the actual drawing logic runs inside React's asynchronous `useEffect` hook *after* the DOM renders, a visible blank/white canvas gap is shown between the DOM commit (which clears the canvas) and the subsequent redraw loop. This creates severe, continuous flickering.
2.  **High-Frequency State Triggers**:
    During mouse dragging, `mousemove` events fire at high frequency (often 60–120Hz). On each event, the handlers call state setters (`setOffset`, `setPanStart`, `setDrawingBbox`). Every single callback triggers a synchronous or batched React component re-render, worsening the buffer clear.
3.  **Render-Cycle Console Debug Logs**:
    Lines 50–59 contains a render-cycle debug logger with no dependency array:
    ```typescript
    useEffect(() => {
      console.group('AnnotationCanvas render debug');
      // ... console logging ...
      console.groupEnd();
    });
    ```
    This log executes blocking writes to the browser console on every single render. It blocks the main thread during high-frequency drag inputs, causing severe lagging, frame drop, and canvas stutter.

---

## 5. Scroll Zoom Analysis
The zoom handler in `AnnotationCanvas.tsx` (Lines 281–299) behaves in a hypersensitive manner:

```typescript
const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
  e.preventDefault();
  const zoomIntensity = 0.08;
  // ...
  const zoomFactor = e.deltaY < 0 ? (1 + zoomIntensity) : (1 - zoomIntensity);
  const nextScale = Math.max(0.12, Math.min(6, scale * zoomFactor));

  setOffset({
    x: mouseX - imgX * nextScale,
    y: mouseY - imgY * nextScale
  });
  setScale(nextScale);
};
```

### The Hypersensitivity Flaw
The zoom factor uses a ternary check `e.deltaY < 0` to decide if the scroll action is in or out. It zooms the canvas by a fixed step of **8% per event**, completely ignoring the magnitude of `e.deltaY`.
*   Modern trackpads and high-precision scroll wheels issue a rapid stream of wheel events with very small fractional `deltaY` values (e.g., `0.5`, `1`).
*   Because the code treats any non-zero `deltaY` as a full zoom tick, scrolling slightly on a trackpad triggers dozens of wheel events in milliseconds, multiplying the scale by $1.08^{N}$. This results in extreme magnification jumps.
*   The separate update calls (`setOffset` and `setScale`) cause double state triggers that can mismatch alignment during high-frequency scrolls.

---

## 6. Project Setup Summary
Based on `package.json`, the project configuration details are:

*   **Bundler & Dev Server**: Vite (`v6.2.3`) using `@vitejs/plugin-react` (`v5.0.4`) and TailwindCSS integration (`v4.1.14`).
*   **Transpiler**: TypeScript (`v5.8.2`) executing type safety checks in strict mode via `tsc --noEmit`.
*   **Core UI Libraries**: React `19.0.1`, React DOM `19.0.1`, Lucide-React `0.546.0` (icons), Motion `12.23.24` (animation).
*   **State Management**: Zustand `5.0.14`.
*   **Backend Client API**: `@google/genai` `2.4.0`.
*   **Testing Setup**: **None**. There is no testing framework configured in `package.json` (no Vitest, Jest, Cypress, or canvas-mocks), nor are there any test scripts or test files inside the codebase.

---

## 7. Recommended Refactoring Strategy

We recommend a non-intrusive refactoring strategy to address flickering, smooth out the scroll zoom, and optimize state management.

### Strategy 1: Bypass React Component Updates during Mouse Dragging (rAF Loop)
To resolve flickering and speed up dragging, decouple canvas drawing coordinates from React state.
1.  **Introduce a Graphics Ref**: Define a React `useRef` to store mutable canvas transformation variables (e.g. `transformRef = useRef({ scale: 1, x: 0, y: 0, isDragging: false, drawingBbox: null })`).
2.  **Mutate transformation values directly inside event handlers**: On mouse move or wheel scroll, update the values directly inside the `transformRef.current` object instead of calling `setOffset`, `setScale`, or `setDrawingBbox`.
3.  **Render via requestAnimationFrame (rAF)**:
    *   Maintain a draw function that reads coordinates from the `transformRef.current` and paints the background image and annotations directly onto the canvas.
    *   Call this draw function inside a `requestAnimationFrame` block whenever a mouse movement or zoom event is detected.
    *   This limits canvas painting to match the monitor's refresh rate (usually 60/120Hz) and keeps mouse state transitions synchronous.
4.  **Decouple Canvas dimensions from JSX attributes**:
    *   Remove `width={resizedDimensions.width}` and `height={resizedDimensions.height}` from the `<canvas>` component attributes in JSX.
    *   Instead, set canvas dimensions (`canvas.width` and `canvas.height`) only once inside a `useLayoutEffect` when the parent container elements resize, or inside the `ResizeObserver` callback. This prevents React from resetting the canvas buffer during normal drag movements.

### Strategy 2: Remove React Context in favor of Direct Zustand Selectors
*   Delete `src/context/AnnotationContext.tsx` and the `AnnotationProvider` wrapper entirely.
*   In `AnnotationCanvas.tsx`, `Annotate.tsx`, and other components, replace the `useAnnotation()` hook with specific Zustand store selector queries:
    ```typescript
    // Inside AnnotationCanvas.tsx:
    const activeModelTab = useAnnotationStore(state => state.activeModelTab);
    const workingDetections = useAnnotationStore(state => state.workingDetections);
    const addDetection = useAnnotationStore(state => state.addDetection);
    const hoveredDetectionIndex = useAnnotationStore(state => state.hoveredDetectionIndex);
    const setHoveredDetectionIndex = useAnnotationStore(state => state.setHoveredDetectionIndex);
    ```
    This ensures components only re-render when the exact variables they subscribe to change, preventing unrelated global state edits (like alerts or console log streams) from triggering canvas refreshes.

### Strategy 3: Implement Logarithmic, Normalized Scroll-Wheel Zoom
*   Modify `handleWheel` in `AnnotationCanvas.tsx` to read the magnitude of `e.deltaY` and apply normalization.
*   Compute the zoom factor using an exponential scale based on the event delta to smooth trackpad movements:
    ```typescript
    const delta = e.deltaY;
    const zoomIntensity = 0.0015; // smooth scaling multiplier
    const zoomFactor = Math.exp(-delta * zoomIntensity);
    const nextScale = Math.max(0.12, Math.min(6, scale * zoomFactor));
    ```
    This ensures trackpads (which fire tiny deltas) zoom in small increments, while mechanical mice (which fire large deltas) zoom in larger steps, providing a smooth and uniform user experience.

### Strategy 4: Clean Up Diagnostic Loggers and Split Components
*   **Remove the blocking render log**: Delete the debug `useEffect` block in `AnnotationCanvas.tsx` lines 50–59 or replace it with a single-run log on mount.
*   **Deconstruct Annotate/Compare Components**: Split the inline layout mapping tables and panels in `Annotate.tsx` and `Compare.tsx` into subcomponents to localize React rendering.
