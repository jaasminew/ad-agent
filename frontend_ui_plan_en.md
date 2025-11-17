# Video Workflow UI Specification (English)

## Goals
- Provide a clear, three-column control room for the autonomous agent workflow.
- Keep the visuals minimal—white/black primary palette with accent `#6467F0` reserved for emphasis.
- Build the screen entirely with existing [shadcn/ui](https://ui.shadcn.com) primitives unless a bespoke wrapper is unavoidable.

## Layout Overview
```
| User Input | Node Timeline | Final Output |
```
- Full-width container with fixed padding (`px-8 py-6`) and muted background (`bg-background`).
- Use `ResizablePanelGroup` (horizontal) if we need adjustable widths; otherwise a `Grid` with `grid-cols-12 gap-6`.
- Recommended column widths: 3 / 5 / 4 units on desktop; collapse to stacked cards on mobile (`md:grid-cols-12`, `sm:flex-col`).

## Left Column – User Input Panel
- Wrapper: `Card` with `CardHeader`, `CardContent`, `CardFooter`.
- Inputs (choose what's relevant to the workflow):
  - `Input` for title / prompt text.
  - `Textarea` for extended instructions.
  - Optional `Select` for template presets.
- Action buttons inside `CardFooter`:
  - `Button` (`variant="default"`) labeled **Generate**. Attach workflow start handler.
  - `Button` (`variant="destructive"`) labeled **Interrupt**. Disabled when workflow idle.
- Add a `Helper` row (`Alert` with `variant="default"`) to show validation or agent status if needed.

## Middle Column – Node Timeline Panel
- Wrapper: `Card` with `ScrollArea` (height `calc(100vh - header)` on desktop).
- Title row contains the workflow name; remove the progress bar.
- Nodes rendered as a vertical list:
  - When the workflow is running, the entire node stack is read-only—use `aria-disabled`, `pointer-events-none`, and `cursor-not-allowed` on hover to indicate nodes cannot be clicked.
  - Use `Timeline` pattern (stack of `Card`s) or a custom flex column with a `Separator` between nodes.
  - Constrain every node card to `max-h-[30vh]` (≈30% viewport height) and `max-w-[80%]` of the column; wrap its content with `ScrollArea` or `overflow-y-auto` so long transcripts gain their own scrollbar.
  - Each node card includes:
    - Header with node label (`Scripter`, `Storyboard Images`, `Video Generation`, `Video Concatenation`, `BGM`).
    - Status badge using `Badge` (`variant="secondary"` for idle, `variant="outline"` for completed). When a node is executing, upgrade border color to `#6467F0`.
    - Running nodes lock out all interactions (`pointer-events-none`, `cursor-not-allowed` on hover). Render real-time streaming text (chat-style feed) instead of skeleton placeholders so users can watch partial output scroll in.
    - Idle or completed nodes can show compact summaries or thumbnails.
- Highlighting while agent works:
  - Wrap the entire column in `cn("border", isRunning ? "border-[#6467F0]" : "border-muted")`.
  - Apply subtle glow via `shadow-[0_0_0_1px_#6467F0]` only during execution.
- Toast feedback:
  - Use shadcn `useToast`. When the workflow ends successfully, push a success toast pinned near the top of the middle column (position via `ToastViewport` anchored above this card).
  - If the run is interrupted or stops mid-way, show a destructive toast labeled “Failed” in the same position to keep messaging consistent.

## Right Column – Final Output Panel
- Wrapper: `Card` with vertical spacing.
- Content order:
  1. Title (`<h2>` styled via `CardHeader`).
  2. Final video player: use native `<video controls>` nested inside `AspectRatio` (16:9). Source set to generated MP4 URL.
  3. Script text in `ScrollArea` with monospace font or `Prose` styling.
  4. `Separator`.
  5. `Button` labeled **Regenerate** (variant `outline`). This restarts only the final render logic.
- Empty / loading states:
  - Use `Skeleton` blocks until video + script exist.
  - Display `Alert` with fallback message if the agent failed.

## Interaction States
- **Idle**: Generate enabled, Interrupt disabled; middle column border muted; nodes show `Badge` = “Waiting”.
- **Running**: Generate disabled, Interrupt enabled; middle column border `#6467F0`; each node flips through statuses (`Waiting → Running → Done`).
- **Interrupted/Error**: Show `Alert variant="destructive"` near top of middle column; keep unfinished nodes flagged.
- **Regeneration**: Trigger resets right column outputs but preserves prior data in a collapsible `Accordion` for history if needed.

## Responsiveness & Accessibility
- Stack columns vertically under `md` breakpoint; each becomes a full-width `Card`.
- Ensure all buttons expose `aria-pressed` or `aria-busy` when relevant.
- Provide captions or transcripts alongside the video when available.
- Accent color (`#6467F0`) used only for active borders, badges, and key icons to maintain contrast.

## Data Wiring
- Use a shared workflow context/store (e.g., `zustand` or React context) to broadcast node status and outputs.
- Node list driven by an ordered array so new steps can be inserted without touching layout.
- Final output panel subscribes to the same store for script + video URL; regenerate posts to the backend agent endpoint.

## Notes
- No progress bar because total duration is indeterminate.
- Keep typography consistent with shadcn defaults (`font-sans`, `text-sm`/`text-base`).
- Audit the theme tokens so dark mode still respects the black/white + accent palette.

