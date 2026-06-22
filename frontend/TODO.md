# Frontend To-Do

## Foundation

- [x] Scaffold the Vite + React + TypeScript app.
- [x] Add the project shell with header, canvas, sidebar, and footer.
- [x] Make the UI boot with mock data when bundles are missing.
- [x] Configure Docker and Make targets for the frontend.

## Data contracts

- [x] Define the bundle schemas for meta, communities, containment, word graph, inverted index, and text store.
- [x] Add local fixtures that match the bundle contracts.
- [x] Implement a loader that prefers real bundles and falls back to mocks.

## Visualization core

- [x] Implement the canvas renderer.
- [x] Implement camera pan and zoom.
- [x] Implement node picking and hover feedback.
- [x] Implement a basic force layout or seeded positioning strategy.

## Navigation and semantics

- [x] Implement zoom-based coexistence between communities, comments, sentences, and words.
- [x] Implement breadcrumb navigation over the focused path.
- [x] Implement brushing via inverted index.
- [x] Implement search and filters.

## Offline bundle generation

- [x] Implement `scripts/build_bundle.py`.
- [x] Generate compact bundles from `final_graph.json` and `communities.json`.
- [x] Wire the frontend to consume generated bundles when available.

## Quality

- [x] Add tests for loader, schema validation, and navigation state.
- [x] Add a smoke test for the mock-only startup path.
- [x] Validate the visual shell against the prototype.
