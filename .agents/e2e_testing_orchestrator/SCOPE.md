# Scope: E2E and Unit Testing Track

## Architecture
- Setup testing infrastructure using Vitest, JSDOM, React Testing Library, and vitest-canvas-mock/mocking.
- Implement unit tests and E2E/integration tests in a decoupled, requirement-driven, opaque-box manner.
- Validate Canvas features: flickering elimination (refs instead of state, event redraw), scroll zoom sensitivity, floating toolbar, page changes.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | Infra Setup | Install Vitest, jsdom, canvas-mock; configure Vitest; add test scripts in package.json | None | PLANNED |
| M2 | Tier 1: Feature Coverage | Test basic rendering, flicker-free refs, wheel zoom step, floating zoom buttons, reset behavior | M1 | PLANNED |
| M3 | Tier 3: Boundary & Corner Cases | Test extreme zoom limits, zero/negative inputs, empty page lists, unmounted events cleanup | M2 | PLANNED |
| M4 | Tier 4: Cross-Feature Combinations | Test interactive zoom+pan, page switch resetting zoom, concurrent wheel and button operations | M3 | PLANNED |
| M5 | Tier 5: Real-World Scenarios | Simulate full user workflows (loading a document, zoom in, panning to find ADE/DL/GT, switching page and checking reset) | M4 | PLANNED |
| M6 | Finalization | Run all tests, perform verification, generate TEST_INFRA.md and TEST_READY.md at project root | M5 | PLANNED |
