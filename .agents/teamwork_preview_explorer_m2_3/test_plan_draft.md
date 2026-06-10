# Test Design Plan: Medical Document Layout Annotator

This document outlines the comprehensive test plan designed for the Medical Document Layout Annotator application. It spans four distinct tiers, progressing from isolated unit-level verification up to complete end-to-end user workflows.

---

## Table of Contents
1. [Test Strategy Overview](#test-strategy-overview)
2. [Target Features under Test](#target-features-under-test)
3. [Testing Infrastructure & Tooling](#testing-infrastructure--tooling)
4. [Tier 1: Unit Level Tests (25 Cases)](#tier-1-unit-level-tests-25-cases)
5. [Tier 2: Integration Level Tests (25 Cases)](#tier-2-integration-level-tests-25-cases)
6. [Tier 3: Cross-Feature Interactions (5 Cases)](#tier-3-cross-feature-interactions-5-cases)
7. [Tier 4: Real-World Workflows (5 Cases)](#tier-4-real-world-workflows-5-cases)
8. [Execution & Automation Commands](#execution--automation-commands)

---

## Test Strategy Overview
The test strategy balances isolated functional verification with end-to-end workflow validation. Given the interactive and graphic-heavy nature of the application (rendering medical document overlays on an HTML5 canvas), testing focuses heavily on coordinate transformations, state-driven rendering logic, layout calculations, and interaction isolation.

The tests are organized into four tiers:
*   **Tier 1: Unit Level Tests**: Verify isolated functions, React hooks, state-selectors, event calculations, and color mappings. Focuses on checking that updates do not trigger unnecessary React component re-renders.
*   **Tier 2: Integration Level Tests**: Validate interactions between components, custom hooks, and the Zustand state store under simulated user events (scrolls, pans, clicks, drags).
*   **Tier 3: Cross-Feature Interactions**: Verify scenarios where multiple features interact, ensuring state transitions, zooms, page resets, and tool settings do not conflict.
*   **Tier 4: Real-World Workflows**: Walk through end-to-end user paths to ensure user journeys remain stable, performance is smooth, and data is persisted correctly.

---

## Target Features under Test
1.  **Canvas Flickering & Event Redraw**: Ensures transient canvas coordinates (scale, offset, panning/drawing states) are stored in React `useRef` to bypass React rendering cycles. Canvas width/height properties must change only on container resize. Redraws are triggered synchronously by canvas event listeners.
2.  **Scroll Zoom Sensitivity & Throttling**: Standardizes zoom direction by inspecting `Math.sign(e.deltaY)` and applying a fixed calibrated scale multiplier. Cursor coordinates under the mouse must map to the same image pixels before and after scale transformations. Scaling events must be throttled to 60 FPS.
3.  **Zoom Toolbar Controls**: Magnifier overlay functions ("Zoom In", "Zoom Out", "Reset Fit") zoom the page centered on the viewport. Zoom percentages format correctly as text (`100%`, `150%`), and buttons are capped at boundaries.
4.  **Page Switch Reset**: Switching document pages resets the zoom scale, centers the pan offsets, and clears transient interactive states (hover index, undo/redo stack, ongoing draw shapes).
5.  **Annotation Detections**: Map bounding boxes onto the canvas context. Handles mouse-over hover checks to highlight boxes, draw interactive dashed helper rectangles during mouse drags, validate minimum drag sizing thresholds (6x6 pixels), and add new annotations via state actions.

---

## Testing Infrastructure & Tooling
*   **Testing Library**: React Testing Library (RTL) for mounting components and firing events.
*   **Test Runner**: Vitest for fast, ESM-native execution.
*   **DOM Environment**: JSDOM to simulate the browser environment.
*   **Canvas Mocking**: `vitest-canvas-mock` to mock `HTMLCanvasElement.prototype.getContext` and inspect draw calls (e.g., `strokeRect`, `fillRect`, `drawImage`, `translate`, `scale`).
*   **State Store Mocking**: Jest-style spies on the Zustand store to intercept action dispatches.

---

## Tier 1: Unit Level Tests (25 Cases)
Unit tests verify the isolated execution of canvas maths, selectors, and individual component features.

### Feature 1: Canvas Flickering & Event Redraw
| Test ID | Test Case Title | Objective | Preconditions | Inputs / Actions | Expected Output / Assertions |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **UT-F1-01** | Ref-Based Panning Isolation | Verify high-frequency panning updates refs directly instead of triggering React re-renders. | `AnnotationCanvas` is mounted. A render counter is tracked. | Simulate cursor movement in pan mode (100 sequential events). | React component render count remains exactly 1. |
| **UT-F1-02** | Ref-Based Zooming Isolation | Verify high-frequency wheel scroll events do not trigger React re-renders. | `AnnotationCanvas` is mounted with a mock image. | Dispatch 20 wheel scroll events rapidly on the canvas element. | Component render count remains exactly 1. |
| **UT-F1-03** | Canvas Property Stability | Verify canvas width and height properties are not mutated during pan/zoom. | `AnnotationCanvas` is mounted inside container. | Simulate drag panning of 300px and zoom scale to 2.5. | Canvas element DOM attributes `width` and `height` do not change. |
| **UT-F1-04** | Event-Driven Redraw Execution | Verify canvas redraw is called on events but does not execute continuously. | Canvas 2D Context `clearRect` is spied on. | Simulate a mousemove event in pan mode, then leave canvas idle. | `clearRect` is called exactly once per event and 0 times during idle. |
| **UT-F1-05** | Event Listener Cleanup | Verify unmounting the canvas removes all attached event listeners. | `AnnotationCanvas` is mounted. Native `removeEventListener` is spied. | Unmount the canvas component from the DOM. | `removeEventListener` is called for `mousedown`, `mousemove`, `mouseup`, and `wheel`. |

### Feature 2: Scroll Zoom Sensitivity & Throttling
| Test ID | Test Case Title | Objective | Preconditions | Inputs / Actions | Expected Output / Assertions |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **UT-F2-01** | Math.sign Zoom Direction | Verify scroll direction is evaluated via `Math.sign`, ignoring scroll step magnitude. | `AnnotationCanvas` is mounted. | Dispatch a wheel event with `deltaY: -3` and another with `deltaY: -120`. | Both inputs increase the zoom scale by the exact same fixed step factor. |
| **UT-F2-02** | Fixed Zoom Increment Step | Verify zoom actions use a configured zoom scale step multiplier. | `AnnotationCanvas` scale ref is initialized to 1. | Dispatch one zoom-in scroll event (`deltaY: -10`). | Scale factor changes from 1 to `1 * (1 + zoomIntensity)` (e.g. 1.08). |
| **UT-F2-03** | Zoom Scale Clamping Limits | Verify scale values cannot exceed max or drop below min constraints. | Max limit is 6.0, Min limit is 0.12. | Dispatch 100 consecutive zoom-in scroll events, then 100 zoom-out events. | Scale value is capped at 6.0 at max, and 0.12 at min. |
| **UT-F2-04** | Cursor Translation Offset Math | Verify calculation to keep cursor position fixed on the document image during zoom. | Initial scale = 1, offsets = (0,0). Cursor at (100, 100). | Zoom in to scale = 2 centered at the cursor. | New offset coordinates calculated shift to (-100, -100) keeping cursor mapped. |
| **UT-F2-05** | Fallback on Zero Delta | Verify canvas handles scroll gestures with zero deltaY safely without NaN values. | `AnnotationCanvas` is active. | Dispatch a scroll wheel event where `deltaY: 0`. | Zoom scale and offset refs do not change and remain as real numbers. |

### Feature 3: Zoom Toolbar Controls
| Test ID | Test Case Title | Objective | Preconditions | Inputs / Actions | Expected Output / Assertions |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **UT-F3-01** | Zoom In Button Step | Verify clicking zoom-in button increases scale by a fixed step. | Scale ref is 1.0. | Trigger click on Zoom In button (`#zoom_in_btn`). | Scale value increases by exactly `0.15` (to 1.15). |
| **UT-F3-02** | Zoom Out Button Step | Verify clicking zoom-out button decreases scale by a fixed step. | Scale ref is 1.0. | Trigger click on Zoom Out button (`#zoom_out_btn`). | Scale value decreases by exactly `0.15` (to 0.85). |
| **UT-F3-03** | Frame Fit Reset | Verify clicking reset fitting centers and scales the image. | Scale is 4.0, offset is (-500, -300). Image size is 800x1000. | Trigger click on Zoom Reset button (`#zoom_reset_btn`). | Scale matches calculated fitScale, and offsets center the page inside viewport. |
| **UT-F3-04** | Zoom Percentage Formatting | Verify scale factor formats correctly as readable text. | Scale changes from 1.0 to 1.5, then to 0.75. | Render percentage text label. | Label text outputs "100%", "150%", and "75%" respectively. |
| **UT-F3-05** | Bound Limit Toolbar States | Verify Zoom In/Out actions are blocked at bounds. | Scale is at 6.0 (max) or 0.12 (min). | Trigger Zoom In at max, or Zoom Out at min. | Scale remains at limits; buttons display disabled styling if bounds are hit. |

### Feature 4: Page Switch Reset
| Test ID | Test Case Title | Objective | Preconditions | Inputs / Actions | Expected Output / Assertions |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **UT-F4-01** | Default Fit-Scale on Page Switch | Verify zoom scale resets to fit-to-screen on loading new page. | Page changes from index 0 to index 1. Scale on page 0 is 3.5. | Dispatch a page change action to index 1. | Scale resets to default fitScale. |
| **UT-F4-02** | Offset Calibration on Page Switch | Verify pan coordinates reset to center the new image layout. | Page changed to index 1. Offset on page 0 was (-400, 200). | Dispatch page change action. | Offset coordinates reset to center page 1 inside the canvas bounds. |
| **UT-F4-03** | Hover Index Clear on Page Switch | Verify hovered annotation index is cleared on page change. | `hoveredDetectionIndex` is 4. | Dispatch page change action. | `hoveredDetectionIndex` resets to `null`. |
| **UT-F4-04** | Undo Stack Purging | Verify delete-undo operations stack is cleared on page change. | `undoStack` contains 3 deleted items from Page 1. | Dispatch page change action to Page 2. | `undoStack` is empty `[]`. |
| **UT-F4-05** | Active Draw State Discard | Verify active drag coordinates are cleared if page changes mid-drag. | User is drawing (`isDrawing` is true, `drawingBbox` is populated). | Dispatch page change action. | `isDrawing` resets to `false`, `drawingBbox` and `drawStart` are set to `null`. |

### Feature 5: Annotation Detections
| Test ID | Test Case Title | Objective | Preconditions | Inputs / Actions | Expected Output / Assertions |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **UT-F5-01** | BBox Stroke & Fill Rendering | Verify detections are drawn on canvas with the correct style colors. | A list of detections is passed. Canvas context is spied. | Trigger canvas drawing cycle. | `ctx.strokeRect` and `ctx.fillRect` are called with colors matching bounding box classes. |
| **UT-F5-02** | Coordinate Bounding Check | Verify hit detection locates the bbox at cursor coordinates. | Bounding box at `[100, 100, 200, 200]`. | Check coordinates (150, 150) and (250, 250). | Hit test returns detection index for (150, 150) and returns `null` for (250, 250). |
| **UT-F5-03** | Draw Mode Tab Protection | Verify drawing boxes is disallowed outside of the GT layer. | Active model tab is 'ADE' or 'DL' (not 'GT'). | Click and drag on canvas in Draw mode. | Canvas displays alert warning and does not update drawing refs. |
| **UT-F5-04** | Drag Minimum Threshold | Verify box creation is skipped if drag dimensions are too small. | Canvas is in Draw Mode on GT. Minimum size threshold is 6px. | Drag a box from (50, 50) to (53, 54) (width=3, height=4). | Canvas `addDetection` action is NOT called on MouseUp. |
| **UT-F5-05** | Color Map Class Resolving | Verify helper resolves correct classification color values. | Look up colors for class `title`, `table`, and `formula`. | Resolve colors using `CLASS_COLORS`. | Returns exact corresponding HEX color strings from design tokens. |

---

## Tier 2: Integration Level Tests (25 Cases)
Integration tests verify how multiple layers (e.g. Canvas, Zustand State Store, and Toolbar UI) interact.

### Feature 1: Canvas Flickering & Event Redraw
| Test ID | Test Case Title | Objective | Preconditions | Inputs / Actions | Expected Output / Assertions |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **IT-F1-01** | Panning Offset Canvas Transform | Verify panning updates the translate offset and shifts the canvas view. | Canvas is in pan mode. | Drag mouse from (100, 100) to (150, 120). | Canvas 2D Context `translate` is called with updated offset coords (+50, +20). |
| **IT-F1-02** | Buffer Stability on Pan Event | Verify canvas pixels do not flash blank during continuous dragging. | Canvas element is active. Context operations are spied. | Simulate a rapid drag pan gesture of 20 movements. | DOM attributes of canvas are not re-written, avoiding graphic buffer clearing. |
| **IT-F1-03** | ResizeObserver Reflow Trigger | Verify window resize triggers canvas dimension adjustments. | `ResizeObserver` mock is active. | Resize the parent container width by 150px. | ResizeObserver triggers canvas width/height updates, followed by redraw. |
| **IT-F1-04** | State Modification Propagation | Verify store updates to detections trigger immediate canvas redraws. | `AnnotationCanvas` is rendered with store selector. | Add a detection to the store workspace. | Canvas context draws the new bounding box on the next animation frame. |
| **IT-F1-05** | Image Loading Canvas Redraw | Verify image onload event triggers initial zoom-fit calculation and draw. | Image source changes. Loading spinner is visible. | Image fires onload callback. | Loading spinner disappears; canvas resets scale and renders image. |

### Feature 2: Scroll Zoom Sensitivity & Throttling
| Test ID | Test Case Title | Objective | Preconditions | Inputs / Actions | Expected Output / Assertions |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **IT-F2-01** | Zoom Out Scroll Translation | Verify scrolling out decreases zoom scale and modifies offset positions. | Scale is 1.0. | Dispatch scroll wheel event with `deltaY: 100` (zoom out). | Scale updates to less than 1.0, and canvas offsets adjust correctly. |
| **IT-F2-02** | Zoom In Scroll Translation | Verify scrolling in increases zoom scale and shifts viewport offsets. | Scale is 1.0. | Dispatch scroll wheel event with `deltaY: -100` (zoom in). | Scale updates to greater than 1.0, offsets update. |
| **IT-F2-03** | High-Frequency Event Throttling | Verify rapid wheel inputs are throttled to prevent performance lag. | Throttling mechanism (e.g. `requestAnimationFrame` queue) is active. | Trigger 30 scroll events within 5ms. | Context redraw is executed at most once per animation frame (max 60fps). |
| **IT-F2-04** | Cursor Anchored Translation Shift | Verify zooming at different coordinate points produces distinct offsets. | Center point is (300, 300). Top-left is (10, 10). | Zoom in at center, reset, then zoom in at top-left. | Resulting coordinate translation offsets are mathematically distinct. |
| **IT-F2-05** | Blocked Interactions during Loading | Verify zoom events are ignored when the document image is loading. | `loading` state is true. | Dispatch scroll events on the canvas element. | Scale ref and offset values remain unchanged. |

### Feature 3: Zoom Toolbar Controls
| Test ID | Test Case Title | Objective | Preconditions | Inputs / Actions | Expected Output / Assertions |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **IT-F3-01** | Zoom In Button View Shift | Verify Zoom In button click shifts coordinates centered on container. | Container dimensions are 600x800. Scale = 1.0. | Click the Zoom In button overlay. | Scale increases, and offsets adjust based on viewport center (300, 400). |
| **IT-F3-02** | Zoom Out Button View Shift | Verify Zoom Out button click shifts coordinates centered on container. | Container dimensions are 600x800. Scale = 1.0. | Click the Zoom Out button overlay. | Scale decreases, offsets adjust based on viewport center (300, 400). |
| **IT-F3-03** | Reset Fitting Execution | Verify Reset button centers small vs large images correctly. | A small image (200x200) is loaded in a 600x600 container. | Click the Zoom Reset button. | Fit scale is set to 1.0, offset is set to (200, 200) to center image. |
| **IT-F3-04** | Percentage Indicator Sync | Verify percentage label changes dynamically with scroll zoom. | Scroll zoom updates scale ref to 1.74. | Trigger mouse scroll zoom. | The percentage label text UI displays "174%". |
| **IT-F3-05** | Click Event Propagation Block | Verify double-clicking toolbar buttons does not trigger canvas pans. | Canvas is in Pan Mode. Toolbar button overlaps canvas area. | Double-click the Zoom In button. | Scale increments twice; canvas `isPanning` remains false; view does not drag. |

### Feature 4: Page Switch Reset
| Test ID | Test Case Title | Objective | Preconditions | Inputs / Actions | Expected Output / Assertions |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **IT-F4-01** | Sidebar Navigation Switch | Verify sidebar page selector changes page and resets canvas view. | Canvas has user panning offsets. | Select page 2 from dropdown in sidebar. | Store index changes, canvas resets zoom scale/offsets, and loads page 2 image. |
| **IT-F4-02** | Next/Prev Button Switch | Verify Next Page button resets canvas view zoom/offsets. | Canvas has zoom of 3.0. | Click the Next Page button (`#next_page_btn`) in header. | Store index increments, canvas scale resets to default, and offsets reset. |
| **IT-F4-03** | Page Load Race Protection | Verify rapid page switching cancels prior image loading requests. | User is on page 1 (loading). | Rapidly click Next Page three times. | Prior image load callbacks are discarded; only the final page image is rendered. |
| **IT-F4-04** | Detection Sync on Page Switch | Verify workspace detections update to match the newly loaded page. | Page 1 has 3 annotations, Page 2 has 5 annotations. | Click Next Page. | `workingDetections` in the store updates to 5 items, which render on canvas. |
| **IT-F4-05** | Undo Toast Deactivation | Verify undo notification toast is dismissed on page switch. | Undo toast is visible after deleting an item on Page 1. | Click Next Page. | Undo toast is dismissed; `showUndoToast` state becomes `false`. |

### Feature 5: Annotation Detections
| Test ID | Test Case Title | Objective | Preconditions | Inputs / Actions | Expected Output / Assertions |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **IT-F5-01** | BBox Hover Highlight Trigger | Verify hovering over a bbox sets the index and updates visual style. | BBox index 0 is at coordinates. | Hover mouse over index 0 coordinates. | Store `hoveredDetectionIndex` is set to 0; canvas redraws bbox with highlight borders. |
| **IT-F5-02** | Interactive Dashed Helper Box | Verify dragging mouse in draw mode draws active bounding box guide. | Canvas is in Draw Mode on GT tab. | Mousedown at (50, 50) and drag to (150, 150). | A dashed rectangle is rendered with an overlay showing dimensions "100x100". |
| **IT-F5-03** | New BBox Store Addition | Verify mouseup after drag dispatches addition to state store. | Canvas in Draw Mode. Drag active from (50, 50) to (200, 150). | Release mouse button (mouseup). | `addDetection` is dispatched, adding item to `workingDetections` in store. |
| **IT-F5-04** | Sidebar Item Deletion | Verify clicking delete icon in sidebar updates canvas annotations. | BBox 1 is drawn. Sidebar displays BBox 1. | Click the trash icon next to BBox 1 in sidebar. | Item is removed from store and disappears from the canvas rendering. |
| **IT-F5-05** | Dropdown Class Color Update | Verify changing class in sidebar dropdown updates canvas rendering. | BBox 1 is class `text` (blue). | Select `table` (orange) from the class dropdown in the sidebar. | Store update is dispatched; canvas redraws BBox 1 in orange. |

---

## Tier 3: Cross-Feature Interactions (5 Cases)
Cross-feature tests verify scenarios where multiple subsystems (e.g. Draw Mode, Zoom, and Page Switch Reset) operate concurrently.

### CFT-01: Zoom & Draw Mode Interaction
*   **Objective**: Verify that drawing bounding boxes works correctly while zoomed and panned.
*   **Preconditions**: Canvas scale is zoomed to 2.0. Canvas offset is panned to (-100, -100). Component is in "Draw Box Mode" on "Current GT (Working)" tab.
*   **Input/Action**: Click mouse at screen/canvas relative point (150, 150) and drag to (250, 300), then release mouse.
*   **Expected Output / Assertions**:
    *   The drawn coordinates are mapped from screen space back to image space correctly.
    *   Image space box coordinates calculations: `x0 = (150 - (-100)) / 2 = 125`, `y0 = (150 - (-100)) / 2 = 125`, `x1 = (250 - (-100)) / 2 = 175`, `y1 = (300 - (-100)) / 2 = 200`.
    *   Store `addDetection` is invoked with bounding box `[125, 125, 175, 200]`.

### CFT-02: Hover State Suppression during Drawing Actions
*   **Objective**: Verify hover detection is disabled while drawing a new bounding box.
*   **Preconditions**: An existing bounding box is located at `[100, 100, 300, 300]`. Component is in "Draw Box Mode".
*   **Input/Action**: Click mouse at (400, 400) to start drawing, and drag cursor to (200, 200) (crossing inside the existing bounding box bounds).
*   **Expected Output / Assertions**:
    *   Store `hoveredDetectionIndex` remains `null` throughout the drag.
    *   The existing box does not render with highlight style borders during the drag.
    *   The dashed drawing helper box renders correctly.

### CFT-03: Multi-Page Zoom/Pan State Persistence Isolation
*   **Objective**: Verify page switching resets zoom, and returning to the page shows the reset state (no leak).
*   **Preconditions**: Active document has Page 1 and Page 2. User is on Page 1.
*   **Input/Action**:
    1. Zoom in on Page 1 to 3.0 and pan offset to (-300, -200).
    2. Click "Next Page" to switch to Page 2 (which resets view).
    3. Click "Prev Page" to return to Page 1.
*   **Expected Output / Assertions**:
    *   Page 2 displays in default fitScale and centered offset.
    *   Upon returning, Page 1 displays in default fitScale and centered offset (the previous zoom/pan settings are cleared and not retained).

### CFT-04: Concurrent Scroll-Wheel and Button Zooming
*   **Objective**: Verify toolbar zoom and scroll-wheel zoom work together.
*   **Preconditions**: Viewport scale is initialized to fitScale (e.g. 0.8).
*   **Input/Action**:
    1. Zoom in using mouse scroll-wheel centered at (100, 100) (scale increases to 1.2).
    2. Click the "Zoom In" button on the toolbar (scale increases to 1.35).
    3. Scroll-wheel zoom out centered at (300, 400) (scale decreases to 1.15).
*   **Expected Output / Assertions**:
    *   Scale is computed correctly without errors or jumps.
    *   Viewport offsets update based on respective center coordinates.
    *   Toolbar percentage text updates dynamically at each step ("120%", "135%", "115%").

### CFT-05: Undo Limits after Page Switch
*   **Objective**: Verify undo operations cannot restore deletions from previous pages.
*   **Preconditions**: User is on Page 1, which has ground truth detections.
*   **Input/Action**:
    1. Delete detection index 0 on Page 1 (creates Undo toast).
    2. Click "Next Page" to switch to Page 2.
    3. Attempt to trigger Undo via keyboard shortcut or state action.
*   **Expected Output / Assertions**:
    *   Undo action is a no-op (or disabled).
    *   Page 1 deleted detection is not restored while viewing Page 2.
    *   Returning to Page 1 shows the detection remains deleted.

---

## Tier 4: Real-World Workflows (5 Cases)
Workflow tests verify end-to-end user journeys and state persistence.

### RWW-01: Ground Truth Creation from YOLO Model
*   **Objective**: Verify complete flow of importing model detections, editing annotations, and saving ground truth.
*   **Preconditions**: Active session is in the "results" status. User is on Page 1. The workspace ground truth is empty.
*   **Input/Action**:
    1. Click the "YOLO" button under Set Initial Base Model.
    2. Confirm destructive swapper dialog.
    3. Identify a layout box representing a false positive header and click "Delete".
    4. Click "Undo" on the popup toast to restore it.
    5. Click another text bounding box and change its classification to `section_header` in the sidebar dropdown.
    6. Click "Confirm Page as Ground Truth" button.
*   **Expected Output / Assertions**:
    *   `workingDetections` copy YOLO detections initially.
    *   Destructive dialog overwrites workspace data.
    *   Deletion removes the item from canvas; Undo restores it to the exact index.
    *   Classification type is updated to `section_header`.
    *   Save action triggers a POST request to `/api/session/{id}/save` with modified ground truth array.

### RWW-02: Detailed Layout Verification and Annotation
*   **Objective**: Verify zooming, panning, finding an overlap, drawing an annotation, and saving.
*   **Preconditions**: Session loaded. Current page has 2 text blocks.
*   **Input/Action**:
    1. Hover and scroll wheel zoom to 250% on a specific section.
    2. Switch canvas mode to "Pan / Zoom". Drag layout to pan.
    3. Switch to "Current GT" tab.
    4. Add a new bbox by clicking "Add Bounding Box" button in sidebar.
    5. Edit the new bbox coordinates (`x0, y0, x1, y1`) manually in the input forms to overlap an existing textbox.
    6. Check overlaps warning indicator in sidebar.
    7. Click "Save Page Edits".
*   **Expected Output / Assertions**:
    *   Canvas displays at 2.5x magnification.
    *   Manual coordination inputs update the canvas bounding box coordinates immediately.
    *   Sidebar shows "1 overlapping layout blocks found" warning.
    *   Save edits successfully saves the state to disk.

### RWW-03: Multi-Page Comparison and Correction
*   **Objective**: Verify inspecting multiple pages, comparing model outputs, and resetting workspace.
*   **Preconditions**: Document uploaded with at least 2 pages.
*   **Input/Action**:
    1. Switch between "ADE GT", "DocLayoutYOLO", and "Nemotron" tabs to inspect predictions on Page 1.
    2. Choose "Nemotron" as base model and copy detections.
    3. Click Next Page to move to Page 2.
    4. Switch canvas mode to "Draw Box Mode".
    5. Draw a new bounding box for a figure.
    6. Click "Clear Page" button in footer to reset Page 2.
*   **Expected Output / Assertions**:
    *   Toggling model tabs updates the canvas drawing detections to match corresponding models.
    *   Switching to Page 2 resets zoom.
    *   New figure box is rendered.
    *   "Clear Page" removes all Page 2 annotations, updating `workingDetections` to `[]` and setting page ground truth to `null`.

### RWW-04: Ground Truth Export and Re-Import
*   **Objective**: Verify that exported ground truth JSON is valid and can be loaded back into the application.
*   **Preconditions**: User has confirmed ground truth annotations on Page 1 and Page 2.
*   **Input/Action**:
    1. Click "Export Ground Truth" button.
    2. Click "Reset All Data" on the dashboard to clear the session.
    3. Upload the same PDF to start a new session.
    4. Click "Import JSON Data" button.
    5. Upload the exported JSON file.
*   **Expected Output / Assertions**:
    *   Export triggers download of `ground_truth.json` containing correct page keys and coordinates.
    *   Import parses JSON structure successfully.
    *   Zustand store state is updated; Page 1 and Page 2 ground truth matches the exported values exactly.

### RWW-05: Network Disconnection & Error Recovery
*   **Objective**: Verify application resilience during backend upload failures and boundary errors.
*   **Preconditions**: Network interface is simulated as disconnected, or backend returns 500 error.
*   **Input/Action**:
    1. Upload a PDF and click "Start Pipeline".
    2. Observe pipeline connection failure.
    3. Re-establish network connectivity (mock server ok).
    4. Click "Start Pipeline" again.
    5. Try drawing an annotation box on the read-only "Nemotron" tab.
    6. Switch to "Current GT" and draw a box with mouse drag less than 5px.
*   **Expected Output / Assertions**:
    *   First attempt shows "Pipeline failed" alert and updates logs with `[ERROR]`.
    *   Second attempt recovers, uploads successfully, and starts pipeline.
    *   Drawing on read-only layer triggers alert warning.
    *   Micro-box drag (less than 5px) is discarded (filters click jitter).

---

## Execution & Automation Commands
The designed test cases are fully automatable using the configured testing framework.

### Running the Tests
To execute all tests, use the following commands in the workspace root:

```powershell
# Run all unit and integration tests
npm run test:run

# Run vitest in watch mode (interactive development)
npm run test

# Run tests with code coverage report
npm run test:coverage
```

### Mocking Canvas and Refs in Code
To verify the canvas flickering and redraw characteristics programmatically, the tests will spy on the canvas element's mock 2D rendering context:

```typescript
import { vi, describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { AnnotationCanvas } from './AnnotationCanvas';

describe('Canvas Redraw Stability', () => {
  it('does not re-create canvas buffer on zoom/pan events', () => {
    const { container } = render(
      <AnnotationCanvas detections={[]} imagePath="mock-path.jpg" />
    );
    const canvas = container.querySelector('canvas') as HTMLCanvasElement;
    
    // Spy on canvas width/height properties
    const widthSpy = vi.spyOn(canvas, 'width', 'set');
    const heightSpy = vi.spyOn(canvas, 'height', 'set');
    
    // Simulate mouse movements (pan)
    // Trigger scroll wheel (zoom)
    
    // Assert that width and height setters were NOT called during interactions
    expect(widthSpy).not.toHaveBeenCalled();
    expect(heightSpy).not.toHaveBeenCalled();
  });
});
```
