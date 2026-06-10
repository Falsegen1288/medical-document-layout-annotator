# Handoff Report: Medical Document Layout Annotator Test Plan Design

## 1. Observation

- **Project Milestones**:
  `PROJECT.md` specifies key tasks in the pipeline:
  - Line 23: "M3 | Canvas Flickering Fix | Move zoom, offset, drag coords to refs. Resize canvas in useLayoutEffect/ResizeObserver without resetting buffer. Redraw only on events. Remove blocking render logs."
  - Line 24: "M4 | Scroll Zoom Calibration | Math.sign(e.deltaY) direction mapping, 12% fixed step, throttle scroll inputs (max 60fps), center on cursor"
  - Line 25: "M5 | Zoom Toolbar & Page Reset | Add floating magnifier controls (Zoom In, Zoom Out, Reset 1:1), percentage display, reset zoom/pan on page change"

- **Existing Implementation (AnnotationCanvas.tsx)**:
  - Line 19: `const [canvasMode, setCanvasMode] = useState<'pan' | 'draw'>('pan');`
  - Lines 281-299 (`handleWheel`):
    ```typescript
    const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
      e.preventDefault();
      const zoomIntensity = 0.08;
      const rect = canvasRef.current!.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const imgX = (mouseX - offset.x) / scale;
      const imgY = (mouseY - offset.y) / scale;

      const zoomFactor = e.deltaY < 0 ? (1 + zoomIntensity) : (1 - zoomIntensity);
      const nextScale = Math.max(0.12, Math.min(6, scale * zoomFactor));

      setOffset({
        x: mouseX - imgX * nextScale,
        y: mouseY - imgY * nextScale
      });
      setScale(nextScale);
    };
    ```
  - Lines 301-333 (`zoomIn`/`zoomOut` buttons update scale by 0.15 directly):
    ```typescript
    const zoomIn = () => {
      setScale(prev => {
        const nextScale = Math.min(6, prev + 0.15);
        ...
        return nextScale;
      });
    };
    ```

- **Store Actions (annotationStore.ts)**:
  - `changePage` triggers Page Switch (lines 258-271).
  - `addDetection` handles adding a new bounding box to the ground truth workspace (lines 342-361).

---

## 2. Logic Chain

1. The refactoring targets outlined in `ORIGINAL_REQUEST.md` and `PROJECT.md` require moving transient react states to refs (Feature 1) and introducing custom math centering & uniform throttling (Feature 2) as well as page resets (Feature 4).
2. Direct inspection of `AnnotationCanvas.tsx` confirms that the zoom implementation currently uses React local state (`scale`, `offset`) which triggers full-component re-renders on wheel/mouse move events, causing flickering and stuttering during rendering.
3. Therefore, testing these features requires verification that component re-renders are suppressed while canvas context redraw updates are explicitly triggered.
4. I compiled a 60-test case suite (Tiers 1-4) covering each feature under ideal unit scenarios (Tier 1), boundary/integration cases (Tier 2), cross-feature interactions (Tier 3), and clinical E2E workflows (Tier 4) to ensure high verification coverage for the incoming implementation.
5. The drafted test cases were written to the target workspace folder path: `c:\Users\user\Downloads\medical-document-layout-annotator\.agents\teamwork_preview_explorer_m2_1\test_plan_draft.md`.

---

## 3. Caveats

- We did not write physical Vitest files since the refactoring work has not yet been executed by the implementation agents.
- The threshold values (such as minimum scale limit `0.12`, max limit `6.0`, minimum box drag size `6x6` pixels) are assumed to remain consistent during implementation.

---

## 4. Conclusion

The designed test cases are fully detailed, actionable, and cover all functional specifications of the Medical Document Layout Annotator. They provide the implementer with a clear set of requirements to satisfy.

---

## 5. Verification Method

- Check the content of the drafted file at:
  `c:\Users\user\Downloads\medical-document-layout-annotator\.agents\teamwork_preview_explorer_m2_1\test_plan_draft.md`
- Assert that there are:
  - 25 test cases for Tier 1 (5 per feature).
  - 25 test cases for Tier 2 (5 per feature).
  - 5 test cases for Tier 3.
  - 5 test cases for Tier 4.
  - All test cases are clearly structured with ID, Preconditions, Steps, and Expected Results.
