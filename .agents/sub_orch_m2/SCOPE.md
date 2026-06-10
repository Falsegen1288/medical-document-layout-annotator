# Scope: State Selection Refactor

## Architecture
- Zustand Store (`src/store/annotationStore.ts`): the single source of truth for layout annotations.
- UI Components (`src/App.tsx`, `src/components/AnnotationCanvas.tsx`): subscribe directly to store state slices.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| 1 | Investigate & Plan | Verify codebase references, imports, and verify compiling starting state | None | DONE |
| 2 | Refactor App.tsx | Replace AnnotationProvider with direct Zustand store selectors | M1 | IN_PROGRESS |
| 3 | Refactor AnnotationCanvas.tsx | Replace useAnnotation with direct Zustand store selectors | M2 | IN_PROGRESS |
| 4 | Remove AnnotationContext.tsx | Delete src/context/AnnotationContext.tsx | M3 | IN_PROGRESS |
| 5 | Verify compilation & linting | Verify no typescript/eslint/vite errors, tests pass | M4 | PLANNED |

## Interface Contracts
- `useAnnotationStore`: State access hook from `src/store/annotationStore.ts`.
- React selectors: components must use specific selectors rather than subscribing to the entire store object (e.g., `useAnnotationStore(state => state.hoveredDetectionIndex)`).
