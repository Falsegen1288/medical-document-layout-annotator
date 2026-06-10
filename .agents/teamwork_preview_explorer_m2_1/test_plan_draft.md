# Test Plan Draft: Medical Document Layout Annotator

This document outlines the comprehensive test plan designed for verifying the core functionality, performance, and stability of the Medical Document Layout Annotator.

---

## 1. Feature Index

The test cases are mapped to five core features under verification:
1. **Canvas Flickering & Event Redraw (CF)**: Verifies ref-based view states, single-loop redraw on events, stable resize rendering, and absence of continuous render cycles.
2. **Scroll Zoom Sensitivity & Throttling (SZ)**: Verifies scroll zoom direction calibration (`Math.sign`), cursor-centered scaling, throttling to max 60 FPS, and fixed zoom steps (12%).
3. **Zoom Toolbar Controls (ZT)**: Verifies floating toolbar actions (Zoom In/Out by 15%, Reset to fit/1.0), and dynamic zoom percentage display.
4. **Page Switch Reset (PS)**: Verifies default zoom/pan reset upon page changes, clean aborting of drawing/panning states, and stable image transitions.
5. **Annotation Detections (AD)**: Verifies render-correctness of bounding boxes, coordinate mapping, hover detection indexing, and bounding box drawing/addition.

---

## 2. Test Tiers Overview

- **Tier 1: Basic Unit & Component Verification** (5 per feature, 25 total) — Standard functional path, core state contracts, event hook bindings.
- **Tier 2: Integration, Boundary & Regression Verification** (5 per feature, 25 total) — Edge conditions, rapid events, constraints, failure handling.
- **Tier 3: Cross-Feature Interaction Verification** (5 total) — Overlapping states, mode transitions, concurrent user behaviors.
- **Tier 4: Real-World Clinical Workflows** (5 total) — Full end-to-end user scenarios mimicking real annotator workflows.

---

## 3. Tier 1: Basic Unit & Component Verification

### Feature 1: Canvas Flickering & Event Redraw (CF)

#### TC-T1-CF-01: Single-onload Image Initialization
- **Preconditions**: Canvas component is mounted with a valid image path prop.
- **Steps**:
  1. Render `AnnotationCanvas` with `imagePath="assets/sample_page_1.png"`.
  2. Mock the `Image.prototype.onload` trigger.
- **Expected Results**:
  - Image is stored in the local image ref (`imageRef.current`).
  - Image loading state transitions to false.
  - Component does not execute repetitive render cycles post-load.
- **Verification Strategy**: Spy on component render function. Verify that rendering does not loop after image load.

#### TC-T1-CF-02: Ref-based Pan Coordinates (No-Render Pan)
- **Preconditions**: Component is loaded. Viewport is in "Pan" mode.
- **Steps**:
  1. Trigger mousedown on `#clinical_annotation_canvas` at coordinate `(100, 100)`.
  2. Dispatch mousemove to `(150, 150)`.
- **Expected Results**:
  - Panning offsets are updated directly in `transformRef.current` (e.g. `{ scale: 1, x: 50, y: 50 }`).
  - Component does not trigger a React state re-render during mousemove.
- **Verification Strategy**: Check console logs or wrap component in render-counter. Verify render count is still 1 during active drag.

#### TC-T1-CF-03: ResizeObserver Stable Buffer Update
- **Preconditions**: Canvas container mounted.
- **Steps**:
  1. Mock container resize event to change dimensions from `600x750` to `800x1000`.
  2. Trigger `ResizeObserver` callback.
- **Expected Results**:
  - Canvas width/height properties update.
  - Redraw is invoked once to redraw the image inside the new bounds.
  - Canvas buffer does not flicker or blank out.
- **Verification Strategy**: Verify `canvasRef.current.width` matches `800` and canvas context functions are called.

#### TC-T1-CF-04: Event Listeners Clean Binding/Unmounting
- **Preconditions**: Canvas component is mounted.
- **Steps**:
  1. Unmount the `AnnotationCanvas` component.
- **Expected Results**:
  - Event listeners for `mousedown`, `mousemove`, `mouseup`, and `wheel` are detached.
  - No trailing event triggers generate runtime errors.
- **Verification Strategy**: Spy on `canvas.removeEventListener` and verify they are called on unmount.

#### TC-T1-CF-05: Event-Driven Redraw Execution
- **Preconditions**: Viewport coordinates initialized.
- **Steps**:
  1. Check canvas paint calls upon normal page render.
  2. Verify that there is no active `requestAnimationFrame` loop repeating paint operations.
- **Expected Results**:
  - Canvas context `drawImage` is called only when mouse events or viewport changes occur.
  - Redraw count remains static when the user is idle.
- **Verification Strategy**: Verify `window.requestAnimationFrame` is not used in a recurring loop.

---

### Feature 2: Scroll Zoom Sensitivity & Throttling (SZ)

#### TC-T1-SZ-01: Wheel Zoom-In Increment Calibration
- **Preconditions**: Viewport initialized with `scale = 1.0` and cursor at center.
- **Steps**:
  1. Dispatch `wheel` event on canvas with `deltaY = -100` (scroll up).
- **Expected Results**:
  - `Math.sign(deltaY)` evaluates to `-1`.
  - Zoom factor increases by exactly the fixed step of 12% (new scale = `1.12`).
- **Verification Strategy**: Inspect the current scale stored in `transformRef.current.scale`.

#### TC-T1-SZ-02: Wheel Zoom-Out Decrement Calibration
- **Preconditions**: Viewport initialized with `scale = 1.0`.
- **Steps**:
  1. Dispatch `wheel` event on canvas with `deltaY = 100` (scroll down).
- **Expected Results**:
  - `Math.sign(deltaY)` evaluates to `1`.
  - Zoom factor decreases by exactly the fixed step of 12% (new scale = `0.88`).
- **Verification Strategy**: Verify scale in `transformRef.current.scale` becomes `0.88`.

#### TC-T1-SZ-03: Zoom Cursor Centering
- **Preconditions**: Image loaded. Viewport initialized at scale = 1.0, offset = (0,0).
- **Steps**:
  1. Position mouse at `(200, 300)` on canvas.
  2. Dispatch `wheel` event with `deltaY = -120`.
- **Expected Results**:
  - The image point at `(200, 300)` remains under the mouse cursor.
  - Offset translates correctly according to the scaling formula:
    `newOffset = mousePos - (mousePos - oldOffset) * (newScale / oldScale)`.
- **Verification Strategy**: Assert that computed `transformRef.current.x` and `y` match the target coordinates.

#### TC-T1-SZ-04: Scroll Event Throttling (Max 60 FPS)
- **Preconditions**: Viewport active.
- **Steps**:
  1. Generate 10 `wheel` events within a 10ms window.
- **Expected Results**:
  - Redraw function is invoked at most once during that window.
  - Subsequent inputs are throttled to run at maximum 60 FPS (approx. 16.6ms spacing).
- **Verification Strategy**: Monitor canvas draw counts vs event dispatch counts.

#### TC-T1-SZ-05: Scroll Scale Limits Enforcement
- **Preconditions**: Scale initialized close to bounding limits (e.g., 0.12 or 6.0).
- **Steps**:
  1. When scale is `0.12`, dispatch scroll down event.
  2. When scale is `6.0`, dispatch scroll up event.
- **Expected Results**:
  - Scale remains clamped at `0.12` and `6.0` respectively.
  - No coordinate errors or out-of-bound drifts occur.
- **Verification Strategy**: Assert scale values do not violate limits.

---

### Feature 3: Zoom Toolbar Controls (ZT)

#### TC-T1-ZT-01: Zoom In Button Execution
- **Preconditions**: Viewport scale is `1.0`. Toolbar is visible.
- **Steps**:
  1. Click the `#zoom_in_btn` element.
- **Expected Results**:
  - Scale factor increases by exactly `15%` (scale = `1.15`).
  - Viewport translates smoothly, centering on viewport center.
- **Verification Strategy**: Verify scale increases from `1` to `1.15`.

#### TC-T1-ZT-02: Zoom Out Button Execution
- **Preconditions**: Viewport scale is `1.0`.
- **Steps**:
  1. Click the `#zoom_out_btn` element.
- **Expected Results**:
  - Scale factor decreases by exactly `15%` (scale = `0.85`).
- **Verification Strategy**: Verify scale decreases from `1` to `0.85`.

#### TC-T1-ZT-03: Zoom Reset Button Execution
- **Preconditions**: Viewport scale is panned to `(150, -200)` and zoomed to `2.5`.
- **Steps**:
  1. Click the `#zoom_reset_btn` element.
- **Expected Results**:
  - Scale factor returns to `1.0`.
  - Pan offsets are reset to `(0, 0)`.
- **Verification Strategy**: Assert scale is `1.0` and offset coordinates are `(0, 0)`.

#### TC-T1-ZT-04: Dynamic Zoom Percentage Display
- **Preconditions**: Toolbar displays zoom status.
- **Steps**:
  1. Change scale to `1.50` via scroll wheel.
- **Expected Results**:
  - Percentage text display shows `"150%"`.
- **Verification Strategy**: Read inner text of percentage indicator.

#### TC-T1-ZT-05: Toolbar Button Limit Clamping
- **Preconditions**: Viewport scale is at max limit (`6.0`).
- **Steps**:
  1. Click the `#zoom_in_btn` button.
- **Expected Results**:
  - Button action is either disabled or scale remains clamped at `6.0`.
  - Display continues to read `"600%"`.
- **Verification Strategy**: Verify scale remains `6.0` and display text remains `"600%"`.

---

### Feature 4: Page Switch Reset (PS)

#### TC-T1-PS-01: Page Transition Zoom/Pan Reset
- **Preconditions**: User has zoomed to `2.0` and panned to `(100, 100)` on Page 1.
- **Steps**:
  1. Call `changePage(1)` (switching to Page 2) via the Zustand store.
- **Expected Results**:
  - Viewport scale resets to default fit scale.
  - Viewport offsets reset to center the new page.
- **Verification Strategy**: Inspect scale and offsets immediately after page index update.

#### TC-T1-PS-02: Reset of Active Drawing Bbox on Page Switch
- **Preconditions**: User is mid-drag in draw mode with a valid `drawingBbox` preview.
- **Steps**:
  1. Call `changePage(1)` via store action.
- **Expected Results**:
  - `drawingBbox` is reset to `null`.
  - Canvas drawing overlay is removed.
- **Verification Strategy**: Check that `drawingBbox` is `null` in component state.

#### TC-T1-PS-03: Panning State Cancellation on Page Switch
- **Preconditions**: User has held down mouse button to pan (`isPanning = true`).
- **Steps**:
  1. Trigger page switch.
- **Expected Results**:
  - `isPanning` resets to `false`.
  - Cursor style reverts to default grab/pointer.
- **Verification Strategy**: Check component's `isPanning` ref/state variable.

#### TC-T1-PS-04: Cursor Icon Reset on Page Switch
- **Preconditions**: Canvas cursor is in `grabbing` or `crosshair` state.
- **Steps**:
  1. Change page index.
- **Expected Results**:
  - Cursor element styles reset to `grab` or default pointer.
- **Verification Strategy**: Read style attributes on the canvas DOM element.

#### TC-T1-PS-05: Loader Transition State
- **Preconditions**: Component is loaded with multiple page paths.
- **Steps**:
  1. Trigger page switch.
  2. Observe canvas during image load interval.
- **Expected Results**:
  - Loading flag turns `true`.
  - Spinner/skeleton UI overlay is displayed.
  - Old image is not drawn during loading.
- **Verification Strategy**: Verify DOM element containing `"LOADING"` is visible during transition.

---

### Feature 5: Annotation Detections (AD)

#### TC-T1-AD-01: Correct Painting of Bounding Boxes
- **Preconditions**: Detections loaded: `[{ type: "title", bbox: [10, 20, 100, 150] }]`.
- **Steps**:
  1. Trigger canvas redraw.
- **Expected Results**:
  - Bounding box is drawn with the color assigned to `title` class (`CLASS_COLORS.title`).
  - Text label showing category and index matches.
- **Verification Strategy**: Spy on canvas context `fillRect` and `strokeRect` arguments.

#### TC-T1-AD-02: Hover Detection Update
- **Preconditions**: Bounding box exists at `(10, 20, 100, 150)`. scale = 1.0, offset = (0,0).
- **Steps**:
  1. Dispatch mousemove over coordinates `(50, 80)`.
- **Expected Results**:
  - System identifies hover collision.
  - Store `hoveredDetectionIndex` updates to the index of the box.
- **Verification Strategy**: Assert that `useAnnotationStore.getState().hoveredDetectionIndex` is correct.

#### TC-T1-AD-03: Hover Clears on Mouse Leave
- **Preconditions**: `hoveredDetectionIndex` is set to `0`.
- **Steps**:
  1. Move mouse to canvas coordinates `(0, 0)` (outside all boxes).
- **Expected Results**:
  - `hoveredDetectionIndex` resets to `null` in the store.
- **Verification Strategy**: Assert that `hoveredDetectionIndex` is `null`.

#### TC-T1-AD-04: Draw Preview Dashed Box Rendering
- **Preconditions**: Canvas in `draw` mode.
- **Steps**:
  1. Trigger mousedown at `(100, 100)`.
  2. Drag mouse to `(200, 250)`.
- **Expected Results**:
  - A dashed bounding box preview is drawn from `(100, 100)` to `(200, 250)`.
  - A label tag displays current dimension tag `(100x150)`.
- **Verification Strategy**: Check canvas context call sequence (`setLineDash` must be called).

#### TC-T1-AD-05: Adding Bounding Box on Mouseup (Drag Threshold Met)
- **Preconditions**: Active drawing box dimensions are `100x150` pixels.
- **Steps**:
  1. Release mouse button (mouseup).
- **Expected Results**:
  - Action `addDetection` is invoked with selected category and coordinates.
  - New detection is appended to `workingDetections` in Zustand store.
- **Verification Strategy**: Verify store `workingDetections` length increases by 1.

---

## 4. Tier 2: Integration, Boundary & Regression Verification

### Feature 1: Canvas Flickering & Event Redraw (CF)

#### TC-T2-CF-01: Rendering Separation of Background Canvas from DOM Updates
- **Preconditions**: Multiple annotations on page. Viewport is in pan mode.
- **Steps**:
  1. Rapidly drag the canvas offset back and forth (triggering continuous `mousemove`).
- **Expected Results**:
  - Transform values update inside refs.
  - React devtools does not report component re-renders.
  - No flickering or white screens appear on canvas during panning.
- **Verification Strategy**: Count component function component executions.

#### TC-T2-CF-02: Rapid Resizing Tolerance
- **Preconditions**: Image loaded.
- **Steps**:
  1. Simulate window size vibrating rapidly (e.g. dragging browser edges back and forth).
- **Expected Results**:
  - Canvas does not throw DOM layout exceptions.
  - Image scaling adjusts without losing current zoom center.
- **Verification Strategy**: Verify canvas functions complete without errors.

#### TC-T2-CF-03: Failsafe on Missing or Corrupt Source Images
- **Preconditions**: ImagePath prop is set to an invalid path (`"assets/corrupt.png"`).
- **Steps**:
  1. Mount component.
- **Expected Results**:
  - Error is caught.
  - Loading indicator turns off.
  - Canvas displays standard fallback text: `"Failed to load canvas image"`.
- **Verification Strategy**: Check console error logs and check UI for fallback messaging.

#### TC-T2-CF-04: Tab Change Redraw Integrity
- **Preconditions**: App has tabs for model outputs (`ADE`, `DL`, `NM`, `GT`).
- **Steps**:
  1. Click between tabs rapidly.
- **Expected Results**:
  - Detections overlay changes instantly.
  - Background document image remains cached in memory and does not flash or reload.
- **Verification Strategy**: Ensure `Image` constructor is not called again on tab change.

#### TC-T2-CF-05: Memory Leak Verification on Fast Unmount
- **Preconditions**: Large document is currently loading.
- **Steps**:
  1. Trigger load of page.
  2. Unmount component immediately before loading completes.
- **Expected Results**:
  - Image `onload` and `onerror` event hooks do not fire on unmounted component refs.
  - No memory leaks or setState warnings on unmounted components occur.
- **Verification Strategy**: Verify no runtime warnings are output in console.

---

### Feature 2: Scroll Zoom Sensitivity & Throttling (SZ)

#### TC-T2-SZ-01: Micro-Scroll Wheel Step Normalization
- **Preconditions**: Modern touchpad or smooth-scroll mouse is used.
- **Steps**:
  1. Dispatch `wheel` event with tiny `deltaY = 0.5`.
  2. Dispatch `wheel` event with tiny `deltaY = -0.5`.
- **Expected Results**:
  - The step is normalized via `Math.sign` to yield full 12% zoom intervals.
  - Avoids fractional zoom jitter.
- **Verification Strategy**: Verify scale changes by exactly `0.12` in both instances.

#### TC-T2-SZ-02: Off-Image Zoom Centering
- **Preconditions**: Document image is smaller than canvas.
- **Steps**:
  1. Place cursor on empty canvas space outside the document image bounds.
  2. Scroll to zoom in.
- **Expected Results**:
  - Scale adjusts.
  - Zoom centers correctly relative to cursor position in canvas coords.
- **Verification Strategy**: Ensure computed viewport translations remain stable.

#### TC-T2-SZ-03: High-Frequency Zoom Spam Protection
- **Preconditions**: Fast scroll speed.
- **Steps**:
  1. Send 100 scroll ticks within a single second.
- **Expected Results**:
  - App throttles requests to prevent page crash.
  - Bounding box scaling remains synchronized with background image scale factor.
- **Verification Strategy**: Monitor CPU usage spikes and confirm bounds matching.

#### TC-T2-SZ-04: Zoom Scale Boundary Clamping Behavior
- **Preconditions**: Zoom scale reaches maximum limit (`6.0`).
- **Steps**:
  1. Position mouse cursor at coordinate `(100, 100)`.
  2. Scroll up to exceed scale limits.
- **Expected Results**:
  - Scale factor stops at `6.0`.
  - Coordinates do not shift (no panning offset drift occurs on subsequent scroll attempts).
- **Verification Strategy**: Verify transform offsets remain unchanged when scrolling past limits.

#### TC-T2-SZ-05: Touchpad Pinch-to-Zoom Gesture Translation
- **Preconditions**: Multi-touch touchpad is used.
- **Steps**:
  1. Dispatch wheel events with `ctrlKey = true` (standard pinch-to-zoom mapping in browsers).
- **Expected Results**:
  - Gesture is detected and mapped to zoom-in/zoom-out steps.
  - Scrolling zoom occurs smoothly.
- **Verification Strategy**: Check scale changes reflect pinch gesture delta values.

---

### Feature 3: Zoom Toolbar Controls (ZT)

#### TC-T2-ZT-01: Magnifier Button Viewport Centered Zoom
- **Preconditions**: Image is zoomed at arbitrary coordinate.
- **Steps**:
  1. Click `Zoom In` (+) button.
- **Expected Results**:
  - Zoom centers exactly at viewport center.
  - Image coordinates translate outward uniformly.
- **Verification Strategy**: Confirm translation math centers around `(containerWidth/2, containerHeight/2)`.

#### TC-T2-ZT-02: Click Buffering & Debouncing
- **Preconditions**: Heavy layout page loaded.
- **Steps**:
  1. Double-click or rapid-click the Zoom Out (-) button 5 times within 100ms.
- **Expected Results**:
  - App processes actions in sequence or buffers them without rendering lag.
  - Final scale matches exact cumulative steps (e.g. decreases by 5 * 15% = 75%).
- **Verification Strategy**: Verify final scale is exactly `0.25` (or minimum clamped limit).

#### TC-T2-ZT-03: Zoom Reset from Extreme Coordinates
- **Preconditions**: Image is scaled to `6.0` and panned far off-screen.
- **Steps**:
  1. Click the `#zoom_reset_btn` element.
- **Expected Results**:
  - Image returns to viewport instantly.
  - Zoom factor is 1.0.
  - Display resets to `"100%"`.
- **Verification Strategy**: Check that image center aligns with viewport center.

#### TC-T2-ZT-04: Rounding Control on Percentage Text
- **Preconditions**: Scale updates to fractional values (e.g. from mouse wheel iterations).
- **Steps**:
  1. Scroll wheel so that scale becomes `1.2467`.
- **Expected Results**:
  - Percentage text display rounds appropriately to `"125%"` (no raw floating decimal values).
- **Verification Strategy**: Read element inner HTML text.

#### TC-T2-ZT-05: Toolbar Responsiveness on Container Scale Shifts
- **Preconditions**: Application is viewed on a tablet or split-screen panel.
- **Steps**:
  1. Resize canvas container down to `300px` width.
- **Expected Results**:
  - Floating toolbar wraps cleanly or scales down.
  - Buttons remain interactive and do not overlap canvas modes menu.
- **Verification Strategy**: Check element bounding client rects for overlaps.

---

### Feature 4: Page Switch Reset (PS)

#### TC-T2-PS-01: Page Race Condition Protection
- **Preconditions**: Slow network simulation.
- **Steps**:
  1. Click next page button rapidly: Page 1 -> Page 2 -> Page 3 in 200ms.
- **Expected Results**:
  - Intermediate image requests are aborted or ignored.
  - Component only displays page 3 content when finished.
  - Viewport scale remains fit to page 3 aspect ratio.
- **Verification Strategy**: Inspect loaded image URL matches page 3 path.

#### TC-T2-PS-02: Isolated Page Workspaces
- **Preconditions**: Page 1 has custom user annotations.
- **Steps**:
  1. Switch to Page 2.
  2. Draw annotation on Page 2.
  3. Switch back to Page 1.
- **Expected Results**:
  - Page 1 retains its custom annotations.
  - Page 2 retains only the drawn annotation.
- **Verification Strategy**: Read store `pages` array ground truth values.

#### TC-T2-PS-03: Reset on Page Switch with Broken Images
- **Preconditions**: Page 2 image path is broken, Page 1 is functional.
- **Steps**:
  1. Switch from Page 1 to Page 2.
- **Expected Results**:
  - Zoom/pan scale resets to defaults.
  - Fallback error layout renders at fit scale.
- **Verification Strategy**: Verify console logs catch page image load failure.

#### TC-T2-PS-04: Undo-Redo Stack Reset on Page Switch
- **Preconditions**: Annotations deleted on Page 1 (populating local undo stack).
- **Steps**:
  1. Switch to Page 2.
- **Expected Results**:
  - Undo stack is cleared (`undoStack = []`).
  - Undo notifications / toast messages are cleared from screen.
- **Verification Strategy**: Verify store state `undoStack` length is `0`.

#### TC-T2-PS-05: Persistence of Active Model View Tab
- **Preconditions**: User selects `DL` (DocLayoutYOLO) model tab on Page 1.
- **Steps**:
  1. Switch to Page 2.
- **Expected Results**:
  - Active model tab remains set to `DL`.
  - View displays Page 2's `DL` predictions.
  - Zoom/pan scales are reset to default fit values.
- **Verification Strategy**: Check store `activeModelTab` remains `DL`.

---

### Feature 5: Annotation Detections (AD)

#### TC-T2-AD-01: Box Drag Minimum Dimension Threshold (6x6 pixels)
- **Preconditions**: Draw mode is active.
- **Steps**:
  1. Drag mouse down to create a tiny bounding box measuring `4x4` pixels.
  2. Release mouse button.
- **Expected Results**:
  - No detection is created in store.
  - Drawing box is discarded.
- **Verification Strategy**: Ensure `addDetection` action was not called.

#### TC-T2-AD-02: Read-Only Layers Draw Interlock
- **Preconditions**: Active model tab is set to `ADE` (read-only model layout).
- **Steps**:
  1. Attempt to drag-to-draw on the canvas.
- **Expected Results**:
  - System blocks drawing action.
  - Alert displays warning: `"Please switch the active model layer to 'Current GT (Working)' to draw new bboxes."`
- **Verification Strategy**: Verify no temporary drawing coordinates are set in state.

#### TC-T2-AD-03: Hover Resolution priority for overlapping boxes
- **Preconditions**: Large bounding box contains a smaller box inside it (nested).
- **Steps**:
  1. Place cursor directly over the inner small box.
- **Expected Results**:
  - Smaller box is selected as hovered.
  - Inner box boundary highlights with thickened border.
- **Verification Strategy**: Check `hoveredDetectionIndex` points to smaller box's index.

#### TC-T2-AD-04: Bounding Box Labels Zoom Scale Behavior
- **Preconditions**: Document is zoomed in to `500%`.
- **Steps**:
  1. Inspect labels on bounding boxes.
- **Expected Results**:
  - Bounding box borders and font sizes adjust dynamically so labels remain legible and do not obscure content.
  - Label text matches classification names.
- **Verification Strategy**: Verify context stroke path coordinates and canvas font size calculations.

#### TC-T2-AD-05: Annotation Deletion & Undo State
- **Preconditions**: Multiple annotations exist in workspace.
- **Steps**:
  1. Delete detection index `2`.
  2. Click Undo action.
- **Expected Results**:
  - Element is removed from canvas view.
  - Undo action restores element at its exact index `2` with matching coordinates.
- **Verification Strategy**: Compare store `workingDetections` contents before and after undo.

---

## 5. Tier 3: Cross-Feature Interaction Verification

#### TC-T3-01: Zooming via Mouse Wheel During Active Box Drawing
- **Preconditions**: Canvas is in `draw` mode. User begins dragging a box.
- **Steps**:
  1. Perform mousedown at `(100, 100)` and hold.
  2. Scroll mouse wheel up twice while holding.
- **Expected Results**:
  - Either zoom is blocked during active mouse drag, OR coordinates for the box bounds are re-calibrated in real-time to match the new zoom transformation.
  - The box is created accurately at correct coordinates relative to the underlying image pixels.
- **Verification Strategy**: Assert the added box coordinates correspond correctly to the image space.

#### TC-T3-02: Interrupting Active Box Drawing via Page Switch
- **Preconditions**: Canvas in `draw` mode. User is dragging a box.
- **Steps**:
  1. Trigger mouse down.
  2. Press hotkey or trigger action to change pages.
- **Expected Results**:
  - Drawing action is aborted cleanly.
  - Zoom coordinates reset to defaults.
  - No ghost bounding box is added to the new page.
- **Verification Strategy**: Assert `workingDetections` of the new page does not contain coordinates from the old page drag.

#### TC-T3-03: Resetting Viewport Frame While in Active Draw Mode
- **Preconditions**: Scale is at `4.0` and pan offset is at `(-150, 200)`. Tool is in `draw` mode.
- **Steps**:
  1. Click `#zoom_reset_btn` to reset the viewport.
- **Expected Results**:
  - Viewport scale resets to `1.0` and offsets to `(0, 0)`.
  - Draw mode remains active (e.g. cursor is still a crosshair, drawing is permitted).
- **Verification Strategy**: Verify `scale` ref is `1.0`, `offset` ref is `(0, 0)`, and component `canvasMode` is `"draw"`.

#### TC-T3-04: Model Tab Selection and Canvas Mode Interlock
- **Preconditions**: Active tab is `"GT"` and canvas mode is `"draw"`.
- **Steps**:
  1. Click on model tab `"ADE"` (read-only model predictions).
- **Expected Results**:
  - Canvas mode automatically switches from `"draw"` to `"pan"`.
  - Cursor reverts to `"grab"`.
  - Drawing toolbar is hidden or disabled.
- **Verification Strategy**: Check component mode status after tab change.

#### TC-T3-05: Container Resizing During Active Canvas Panning
- **Preconditions**: User is in the middle of dragging/panning the image.
- **Steps**:
  1. Dispatch mouse down on canvas and move mouse to trigger pan.
  2. Simultaneously trigger window resize callback.
- **Expected Results**:
  - Canvas size changes are handled without throwing exceptions.
  - Coordinates inside `transformRef` remain continuous without jumping or flashing.
- **Verification Strategy**: Ensure pan motion remains smooth during screen adjustments.

---

## 6. Tier 4: Real-World Clinical Workflows

#### TC-T4-01: End-to-End Medical Document Labeling Pipeline
- **Preconditions**: App is initialized on main page workspace.
- **Steps**:
  1. Load clinical PDF file.
  2. Wait for model pipeline execution, navigate to Page 1 results on `GT` tab.
  3. Zoom in to `250%` over a table scan region.
  4. Pan to align the table bounds on canvas.
  5. Select `table` category from category list.
  6. Drag and draw table boundary box.
  7. Delete an accidental overlap.
  8. Click Undo.
  9. Click "Confirm Page Ground Truth" to commit annotations to backend disk.
- **Expected Results**:
  - Bounding box renders stably at `250%` and follows pan.
  - Save operation posts JSON payload successfully to backend `/api/session/save` route.
  - Toast message notifies user of successful save.
- **Verification Strategy**: Spy on network fetch payload. Confirm saved bbox coordinates match user-drawn coordinates.

#### TC-T4-02: Multi-Page Scan Review and Layout Auditing
- **Preconditions**: Workspace is loaded with a 3-page document.
- **Steps**:
  1. Review Page 1 model detections (ADE, DL, NM).
  2. Switch page to Page 2.
  3. Viewport automatically resets zoom/pan.
  4. Zoom in 2.0x, verify table layouts, switch to Page 3.
  5. Viewport resets zoom/pan again.
- **Expected Results**:
  - Layout is clean on every page.
  - Zoom levels adapt to the page's intrinsic boundaries.
  - No coordinate leaks occur between pages.
  - Performance remains smooth (no delay or lag in viewport adjustments).
- **Verification Strategy**: Verify layout resets automatically on each page switch.

#### TC-T4-03: Dense Document High-Precision Annotation
- **Preconditions**: Medical page with multi-column text, tiny footnotes, and formulas.
- **Steps**:
  1. Zoom in to `450%` scale.
  2. Pan to bottom footer section.
  3. Position mouse cursor exactly over a `footnote` text segment.
  4. Add bounding boxes for `footnote` and `formula`.
  5. Verify boxes remain aligned with the document image when zooming out to `100%`.
- **Expected Results**:
  - Viewport remains responsive during high scale factors.
  - BBoxes maintain sub-pixel precision relative to background image.
  - Footnote labels and borders render cleanly.
- **Verification Strategy**: Verify bounding boxes are located at identical normalized image coordinates at all scales.

#### TC-T4-04: Edit History & State Synchronization
- **Preconditions**: Multiple detections on working canvas page.
- **Steps**:
  1. Add annotation boxes `1`, `2`, and `3`.
  2. Delete annotation box `2`.
  3. Undo deletion.
  4. Change model tab to `ADE` and back to `GT`.
  5. Verify box coordinates are unchanged.
- **Expected Results**:
  - Sync remains intact between the Zustand store and the Canvas drawing engine.
  - The undo history stacks operations correctly.
- **Verification Strategy**: Read Zustand `workingDetections` list contents and count of annotations.

#### TC-T4-05: Stress Test with Extreme Document Annotations
- **Preconditions**: Workspace holds a document with 100+ annotations.
- **Steps**:
  1. Zoom and pan rapidly around the canvas container.
  2. Hover back and forth across multiple dense bounding box clusters.
- **Expected Results**:
  - The UI does not lag (remains at 60 FPS).
  - Hover detection returns correct index immediately.
  - Redraw execution takes less than 16ms.
- **Verification Strategy**: Profile the canvas redraw performance using browser performance tools.
