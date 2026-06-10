# Handoff Report — Test Design for Medical Document Layout Annotator

## 1. Observation
*   The project contains a test runner (`vitest`) and testing environment configurations in `package.json` (lines 12-14), `vitest.config.ts`, and `vitest.setup.ts`.
*   The core interactive component is `src/components/AnnotationCanvas.tsx` which contains:
    *   Image load effects and resize observer triggers (lines 34-75).
    *   Scale and offset states for zoom/pan (lines 23-27).
    *   Drawing states (lines 29-32).
    *   Drawing loop executed in a `useEffect` (lines 96-170) triggered by changes to `[image, detections, scale, offset, hoveredDetectionIndex, resizedDimensions, drawingBbox, selectedDrawClass]`.
    *   Mouse handlers (`handleMouseMove`, `handleMouseDown`, `handleMouseUp`, `handleMouseLeave`, `handleWheel`, `zoomIn`, `zoomOut`) on lines 191-333.
*   The state store `src/store/annotationStore.ts` handles the state actions (`changePage`, `addDetection`, `deleteDetection`, `initWorkingDetections`, etc.) on lines 258-452.
*   The draft test design document has been written to `c:\Users\user\Downloads\medical-document-layout-annotator\.agents\teamwork_preview_explorer_m2_3\test_plan_draft.md`.

## 2. Logic Chain
1.  Since the codebase is an interactive SPA using Canvas coordinates mapping to document layouts, ensuring visual and logical stability requires comprehensive testing across different isolation layers (Tiers).
2.  By defining Tiers 1-4 tests (Unit, Integration, Cross-Feature, Workflows) for all 5 key features (Canvas Flickering, Scroll Zoom, Zoom Toolbar, Page Switch Reset, Annotation Detections), we establish robust specifications.
3.  Unit tests (Tier 1) verify that high-frequency mouse actions (scrolling, dragging) update `useRef` values instead of React states, keeping component render counts stable and preventing buffer-clearing canvas flickering.
4.  Integration tests (Tier 2) check the boundary between the store, toolbar elements, and canvas drawing context.
5.  Cross-Feature (Tier 3) and Workflow (Tier 4) scenarios check complex interactions (e.g. page changes during draw gestures, undo stack boundaries, and full YOLO-based GT pipelines).
6.  Specifying test objectives, preconditions, inputs/actions, and expected assertions for all 60 cases provides the implementing developer with an actionable test implementation plan.

## 3. Caveats
*   The test case plan relies on the mocked canvas APIs provided by `vitest-canvas-mock` (e.g. spying on 2D context fillRect/strokeRect calls). Real browser rendering bugs (such as device-specific GPU rasterization issues or layout latency) can only be verified in a real browser via E2E testing tools (like Playwright/Cypress), which are out of scope for the current Vitest suite.
*   Physical mousewheel scroll event speed variation across hardware (e.g., trackpads vs notched mouse wheel clicks) is simulated via delta values; actual user feel might require manual verification on physical devices.

## 4. Conclusion
We have designed a detailed, requirement-driven, opaque-box test design plan containing 60 specific test cases structured into four tiers (25 Tier 1, 25 Tier 2, 5 Tier 3, 5 Tier 4) across the 5 target canvas and annotation features. The document is written and ready for the implementation phase.

## 5. Verification Method
1.  **Inspect Draft Test Plan**: View and verify the written file at `c:\Users\user\Downloads\medical-document-layout-annotator\.agents\teamwork_preview_explorer_m2_3\test_plan_draft.md`.
2.  **Verify Test Runner Configuration**: Run `npm run test:run` in the terminal to verify the test runner executes without config failures, even before new test files are written.
