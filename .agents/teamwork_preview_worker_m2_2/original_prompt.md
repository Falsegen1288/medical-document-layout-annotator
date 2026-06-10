## 2026-06-10T08:27:31Z

You are teamwork_preview_worker_m2_2.
Your working directory is: c:\Users\user\Downloads\medical-document-layout-annotator\.agents\teamwork_preview_worker_m2_2\
Please read the PROJECT.md, SCOPE.md, and aggregated_findings.md files at:
- c:\Users\user\Downloads\medical-document-layout-annotator\PROJECT.md
- c:\Users\user\Downloads\medical-document-layout-annotator\.agents\sub_orch_m2\SCOPE.md
- c:\Users\user\Downloads\medical-document-layout-annotator\.agents\sub_orch_m2\aggregated_findings.md

Your task is to:
1. Refactor `src/App.tsx`:
   - Remove `AnnotationProvider` import and wrapper.
   - Subscribe `MainAppShell` directly to Zustand state slices using selectors:
     - `status = useAnnotationStore(state => state.status)`
     - `pages = useAnnotationStore(state => state.pages)`
     - `uploadedPdfName = useAnnotationStore(state => state.uploadedPdfName)`
     - `currentPageIndex = useAnnotationStore(state => state.currentPageIndex)`
     - `changePage = useAnnotationStore(state => state.changePage)`
     - `confirmPage = useAnnotationStore(state => state.confirmPage)`
   - Update all occurrences of `store.*` in `MainAppShell` to reference the selector variables.
2. Refactor `src/components/AnnotationCanvas.tsx`:
   - Replace import of `useAnnotation` with `useAnnotationStore` from `../store/annotationStore`.
   - Replace `useAnnotation()` hook call with separate selectors:
     - `hoveredDetectionIndex = useAnnotationStore(state => state.hoveredDetectionIndex)`
     - `setHoveredDetectionIndex = useAnnotationStore(state => state.setHoveredDetectionIndex)`
     - `addDetection = useAnnotationStore(state => state.addDetection)`
     - `activeModelTab = useAnnotationStore(state => state.activeModelTab)`
3. Delete `src/context/AnnotationContext.tsx`.
4. Run `npm run lint` (`tsc --noEmit`) and `npm run build` (`vite build`) to verify that the project compiles and lint checks pass. Also run `npm run test:run` to verify tests (if any).
5. Document all commands run and their output in your handoff report (`handoff.md`) in your working directory.
6. Report back when complete.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
