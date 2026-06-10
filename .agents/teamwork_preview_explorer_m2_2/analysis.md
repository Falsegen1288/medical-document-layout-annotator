# Analysis: State Selection Refactor

## Executive Summary
This analysis outlines the strategy for removing `AnnotationContext.tsx` and `AnnotationProvider`, and refactoring `AnnotationCanvas.tsx` and `App.tsx` to subscribe directly to Zustand state slices via store selectors. 

By eliminating the redundant React Context layer and migrating to fine-grained Zustand selectors, we reduce react render propagation, avoid unnecessary component updates when unrelated store fields change, and simplify the state management architecture of the application.

---

## Codebase Starting State Analysis
1. **Compilation & Lint Status**:
   - The project is configured with Vite, TypeScript, and TailwindCSS.
   - The typescript compiler check script is `"lint": "tsc --noEmit"`.
   - The test script is `"test:run": "vitest run"`.
   - Due to sandboxed terminal permission timeouts, running commands locally in the environment is constrained. However, manual inspections confirm the code structure conforms to standard TSX/React 19 configurations.
2. **Current Redundant Context Layer**:
   - `src/context/AnnotationContext.tsx` wraps the whole Zustand store hook `useAnnotationStore()` and creates a standard React Context (`AnnotationContext`).
   - Any updates in the Zustand store trigger a context value change in `AnnotationProvider` because it uses `const store = useAnnotationStore()`, which returns the entire store object.
   - This in turn causes `AnnotationProvider` to re-render, and propagates re-renders to all consumer components using the `useAnnotation()` hook, even if they only depend on a small part of the state (e.g. `hoveredDetectionIndex`).

---

## Detailed Refactoring Strategy

### Phase 1: Refactor `App.tsx`
Replace the usage of the global `useAnnotationStore` hook inside `MainAppShell` with specific selectors. Remove the `AnnotationProvider` wrapping around `<MainAppShell />`.

**Proposed Diff in `src/App.tsx`**:

```diff
<<<<
import { useAnnotationStore } from './store/annotationStore';
import { Dashboard } from './pages/Dashboard';
import { Annotate } from './pages/Annotate';
import { Compare } from './pages/Compare';
import { Export } from './pages/Export';
import { AnnotationProvider } from './context/AnnotationContext';
====
import { useAnnotationStore } from './store/annotationStore';
import { Dashboard } from './pages/Dashboard';
import { Annotate } from './pages/Annotate';
import { Compare } from './pages/Compare';
import { Export } from './pages/Export';
>>>>
```

```diff
<<<<
function MainAppShell() {
  const store = useAnnotationStore();
  const [activeTab, setActiveTab] = useState<AppTab>('dashboard');

  // Automatically reset tab to dashboard if session is reset
  useEffect(() => {
    if (store.status === 'idle') {
      setActiveTab('dashboard');
    }
  }, [store.status]);

  const handleCommitSession = async () => {
    if (store.status !== 'results') {
      alert('No active session to commit.');
      return;
    }
    // Commit the current page changes to the backend
    await store.confirmPage();
    alert('Session successfully committed! Ground truth annotations have been safely saved to the server database.');
  };

  const hasActiveSession = store.status === 'results' && store.pages.length > 0;
====
function MainAppShell() {
  const status = useAnnotationStore(state => state.status);
  const pages = useAnnotationStore(state => state.pages);
  const uploadedPdfName = useAnnotationStore(state => state.uploadedPdfName);
  const currentPageIndex = useAnnotationStore(state => state.currentPageIndex);
  const changePage = useAnnotationStore(state => state.changePage);
  const confirmPage = useAnnotationStore(state => state.confirmPage);

  const [activeTab, setActiveTab] = useState<AppTab>('dashboard');

  // Automatically reset tab to dashboard if session is reset
  useEffect(() => {
    if (status === 'idle') {
      setActiveTab('dashboard');
    }
  }, [status]);

  const handleCommitSession = async () => {
    if (status !== 'results') {
      alert('No active session to commit.');
      return;
    }
    // Commit the current page changes to the backend
    await confirmPage();
    alert('Session successfully committed! Ground truth annotations have been safely saved to the server database.');
  };

  const hasActiveSession = status === 'results' && pages.length > 0;
>>>>
```

```diff
<<<<
            <span className="font-mono text-[9px] text-text-muted uppercase tracking-wider leading-none">Input Source</span>
            <span className="font-mono text-xs text-on-surface font-bold mt-1 truncate max-w-[160px]">
              {hasActiveSession ? store.uploadedPdfName : 'No Active Session'}
            </span>
====
            <span className="font-mono text-[9px] text-text-muted uppercase tracking-wider leading-none">Input Source</span>
            <span className="font-mono text-xs text-on-surface font-bold mt-1 truncate max-w-[160px]">
              {hasActiveSession ? uploadedPdfName : 'No Active Session'}
            </span>
>>>>
```

```diff
<<<<
            {/* Active document footer selector shortcut */}
            <div className="p-4 border-t border-border mt-auto bg-surface-container-lowest/50 text-[11px]">
              <span className="text-text-muted block font-bold uppercase tracking-wider mb-2 font-bold">QUICK FLIP PAGE</span>
              <div className="space-y-1 max-h-36 overflow-y-auto pr-1">
                {store.pages.map((p, idx) => (
                  <button
                    key={p.page}
                    onClick={() => store.changePage(idx)}
                    className={`w-full text-left font-mono truncate py-1.5 px-2 rounded-xs transition-all flex items-center justify-between text-[11px] ${
                      store.currentPageIndex === idx
                        ? 'bg-primary/10 text-primary border border-primary/20 font-bold'
                        : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container border border-transparent'
                    }`}
                  >
                    <span>Page {p.page}</span>
                    {p.ground_truth !== null ? (
                      <span className="text-[9px] bg-primary/20 text-primary px-1 rounded-sm font-bold">✓</span>
                    ) : (
                      <span className="text-[9px] bg-warning/20 text-warning px-1 rounded-sm font-bold">?</span>
                    )}
                  </button>
                ))}
              </div>
            </div>
====
            {/* Active document footer selector shortcut */}
            <div className="p-4 border-t border-border mt-auto bg-surface-container-lowest/50 text-[11px]">
              <span className="text-text-muted block font-bold uppercase tracking-wider mb-2 font-bold">QUICK FLIP PAGE</span>
              <div className="space-y-1 max-h-36 overflow-y-auto pr-1">
                {pages.map((p, idx) => (
                  <button
                    key={p.page}
                    onClick={() => changePage(idx)}
                    className={`w-full text-left font-mono truncate py-1.5 px-2 rounded-xs transition-all flex items-center justify-between text-[11px] ${
                      currentPageIndex === idx
                        ? 'bg-primary/10 text-primary border border-primary/20 font-bold'
                        : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container border border-transparent'
                    }`}
                  >
                    <span>Page {p.page}</span>
                    {p.ground_truth !== null ? (
                      <span className="text-[9px] bg-primary/20 text-primary px-1 rounded-sm font-bold">✓</span>
                    ) : (
                      <span className="text-[9px] bg-warning/20 text-warning px-1 rounded-sm font-bold">?</span>
                    )}
                  </button>
                ))}
              </div>
            </div>
>>>>
```

```diff
<<<<
export default function App() {
  return (
    <AnnotationProvider>
      <MainAppShell />
    </AnnotationProvider>
  );
}
====
export default function App() {
  return <MainAppShell />;
}
>>>>
```

---

### Phase 2: Refactor `AnnotationCanvas.tsx`
Replace imports and calls to `useAnnotation` with imports and calls to `useAnnotationStore` using individual selectors.

**Proposed Diff in `src/components/AnnotationCanvas.tsx`**:

```diff
<<<<
import { Detection, CLASS_COLORS, CLASS_LABELS, DocLayClass } from '../types';
import { useAnnotation } from '../context/AnnotationContext';
import { Maximize, Minimize, RotateCcw, Move, PenTool, Check } from 'lucide-react';
====
import { Detection, CLASS_COLORS, CLASS_LABELS, DocLayClass } from '../types';
import { useAnnotationStore } from '../store/annotationStore';
import { Maximize, Minimize, RotateCcw, Move, PenTool, Check } from 'lucide-react';
>>>>
```

```diff
<<<<
export const AnnotationCanvas: React.FC<AnnotationCanvasProps> = ({ detections, imagePath }) => {
  const { hoveredDetectionIndex, setHoveredDetectionIndex, addDetection, activeModelTab } = useAnnotation();
  const canvasRef = useRef<HTMLCanvasElement>(null);
====
export const AnnotationCanvas: React.FC<AnnotationCanvasProps> = ({ detections, imagePath }) => {
  const hoveredDetectionIndex = useAnnotationStore(state => state.hoveredDetectionIndex);
  const setHoveredDetectionIndex = useAnnotationStore(state => state.setHoveredDetectionIndex);
  const addDetection = useAnnotationStore(state => state.addDetection);
  const activeModelTab = useAnnotationStore(state => state.activeModelTab);

  const canvasRef = useRef<HTMLCanvasElement>(null);
>>>>
```

---

### Phase 3: Remove `AnnotationContext.tsx`
Delete the file `src/context/AnnotationContext.tsx`.

---

## Future Optimization Recommendations
Although out of direct scope for this task, the sub-pages (`Annotate.tsx`, `Compare.tsx`, `Dashboard.tsx`, `Export.tsx`) also invoke `const store = useAnnotationStore()` directly, making them subscribe to the entire store state. 
To improve performance further and completely standardise the state selection layer, it is recommended to refactor these pages in a subsequent milestone using individual selectors:
- **`Dashboard.tsx`**: Extract `selectedPageRange`, `pdfPageCount`, `pdfFile`, `uploadedPdfName`, `pipelineLogs`, `status`, `pages`, `setSelectedPageRange`, `setPdfFile`, `startPipeline`, `resetAllData`.
- **`Annotate.tsx`**: Extract `pages`, `currentPageIndex`, `activeModelTab`, `workingDetections`, `hoveredDetectionIndex`, `showUndoToast`, `toastMessage`, `initWorkingDetections`, `changePage`, `confirmPage`, `setActiveModelTab`, `setHoveredDetectionIndex`, `deleteDetection`, `updateDetection`, `addDetection`, `triggerUndo`, `dismissToast`.
- **`Compare.tsx`**: Extract `pages`, `currentPageIndex`, `modelsFound`, `changePage`.
- **`Export.tsx`**: Extract `pages`, `sessionId`, `importJsonData`, `exportGroundTruth`, `changePage`.

---

## Verification & Testing Plan
After implementing the refactoring changes, run the following verification steps:

1. **Compilation Check**:
   ```bash
   npm run lint
   ```
   *Expected result*: Typescript compile runs cleanly and terminates with zero error exit code.

2. **Vite Production Build Check**:
   ```bash
   npm run build
   ```
   *Expected result*: The build processes JS/CSS assets successfully, outputting compiled static bundle without errors.

3. **Runtime & Interactive Verification**:
   - Launch application locally using `npm run dev`.
   - Upload a test PDF, specify a page range, and verify predictions display on the dashboard.
   - Enter active workspace canvas, verify drawing a bounding box adds it to list.
   - Hover over bounding boxes inside canvas, verify highlighting triggers correctly without console lag or coordinate mismatch.
   - Verify page changing resets zoom level and updates detections appropriately.
