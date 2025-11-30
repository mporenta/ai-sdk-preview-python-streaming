# Agent Instructions

- Use `pnpm` for frontend/package scripts (e.g., `pnpm lint`, `pnpm dev`), and avoid rewriting the lockfile unless dependencies change intentionally.
- Back-end utilities live in `api/`; run `python -m compileall api` as a quick sanity check after Python changes.
- The chat backend streams SSE events expected by the Next.js UI; preserve existing SSE headers and event structure when modifying streaming code.
- Prefer TypeScript/ESLint defaults for UI code and keep message rendering tolerant of assistant replies that may arrive as plain text or structured parts.
- If you add more instruction files under subdirectories, those take precedence for files within their scope.
