# Design Document

*Note: Since the backend is primarily API-driven right now, this document serves as a guideline for the upcoming Phase 4 Frontend UI.*

## 1. Visual Aesthetics
- **Theme**: Premium Dark Mode default with an emphasis on "Glassmorphism" (frosted glass effects).
- **Primary Colors**: 
  - Background: Very dark blue/grey (`#0F172A`)
  - Accent: Electric Indigo (`#6366F1`) or Cyberpunk Cyan (`#06B6D4`)
  - Text: Off-white/slate (`#F8FAFC`, `#94A3B8`)
- **Typography**: 
  - Primary Font: *Inter* or *Geist* for crisp, modern readability.
  - Monospace (for logs/code): *JetBrains Mono* or *Fira Code*.

## 2. Layout & UX
- **Chat Interface**: A central, clean chat interface where the user submits natural language requests.
- **Live Execution Panel**: A side panel or inline component that dynamically renders the LangGraph DAG as it executes. 
  - Nodes flash or pulse (micro-animations) when they are `RUNNING`.
  - Nodes turn green for `SUCCESS` and red for `FAILED`.
- **Approval Modals**: If a task requires manager approval, an interactive, distinct modal should appear for authorized users to click "Approve" or "Reject".

## 3. Interaction Principles
- **Micro-animations**: Hover states on buttons should be smooth. State transitions (like a task completing) should have a satisfying visual pop.
- **Feedback**: Users should never be left waiting without visual indicators. Skeleton loaders or typing indicators must be present while the LLM is planning.
