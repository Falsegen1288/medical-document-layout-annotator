# Synthesis: State Selection Refactor

## Consensus
All three Explorer subagents reached 100% consensus on the following findings and strategy:
1. **Affected Consumers**: Only `src/App.tsx` and `src/components/AnnotationCanvas.tsx` import/consume anything from the React Context layer (`src/context/AnnotationContext.tsx`).
2. **AnnotationProvider removal**: In `src/App.tsx`, we can completely remove the import of `AnnotationProvider` and remove the `<AnnotationProvider>` wrapper around `<MainAppShell />`.
3. **App.tsx Zustand selectors**: `src/App.tsx` currently subscribes to the entire Zustand store via `const store = useAnnotationStore()`. We will replace this with fine-grained selectors:
   - `status = useAnnotationStore(state => state.status)`
   - `pages = useAnnotationStore(state => state.pages)`
   - `uploadedPdfName = useAnnotationStore(state => state.uploadedPdfName)`
   - `currentPageIndex = useAnnotationStore(state => state.currentPageIndex)`
   - `changePage = useAnnotationStore(state => state.changePage)`
   - `confirmPage = useAnnotationStore(state => state.confirmPage)`
4. **AnnotationCanvas.tsx Zustand selectors**: `src/components/AnnotationCanvas.tsx` currently imports `useAnnotation` and extracts context variables. We will replace this with:
   - `hoveredDetectionIndex = useAnnotationStore(state => state.hoveredDetectionIndex)`
   - `setHoveredDetectionIndex = useAnnotationStore(state => state.setHoveredDetectionIndex)`
   - `addDetection = useAnnotationStore(state => state.addDetection)`
   - `activeModelTab = useAnnotationStore(state => state.activeModelTab)`
5. **Context File Removal**: Deleting `src/context/AnnotationContext.tsx` entirely.
6. **Verification**: Run `npm run lint` (`tsc --noEmit`) and `npm run build` (`vite build`) to verify that the project compiles and lint checks pass cleanly.

## Resolved Conflicts
None. All three subagents reported identical analysis results.

## Gaps
None. The code changes required are well-defined and self-contained.
