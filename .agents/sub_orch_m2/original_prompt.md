# Original User Request

## 2026-06-10T08:11:09Z

You are the Sub-orchestrator for Milestone 2: State Selection Refactor.
Your goal is to:
1. Remove `AnnotationContext.tsx` and the `AnnotationProvider` context wrapper.
2. Update all components that consume the context (specifically `AnnotationCanvas.tsx` and `src/App.tsx`) to subscribe to Zustand state slices directly using store selectors (e.g., `useAnnotationStore(state => state.hoveredDetectionIndex)`).
3. Ensure the project compiles and lint checks pass.

Follow the Project Pattern:
- Assess and run the Explorer -> Worker -> Reviewer cycle (spawning workers, reviewers, and auditors) to verify correctness.
- Ensure the worker follows the integrity instructions: do not cheat or hardcode.
- Your working directory is c:\Users\user\Downloads\medical-document-layout-annotator\.agents\sub_orch_m2. Create plans and progress files there. When complete, write handoff.md and send a message.
