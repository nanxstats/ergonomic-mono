# Agent guidelines

- This repo builds Ergonomic Mono from the phooky fork of Office Code Pro.
- Source OTFs are in `Office-Code-Pro/Fonts/Office Code Pro/OTF/`: Light,
  Regular, Medium, Bold, and their Italic companions (eight styles).
- Outputs are `fonts/ErgonomicMono-*.otf`, with preferred family
  `Ergonomic Mono`. Keep naming and bold/italic flags consistent; the
  upstream license reserves "Office Code Pro".
- Keep the slashed `zero` and single-storey `g` as defaults. `ss01` selects
  the existing dotted `zero.alt`; `ss02` selects the imported double-storey
  `g.ss02`. Each style contains all glyph variants.
- Source Code Pro donors are in `source-code-pro/OTF/` (release branch).
  Use matching weights: upright `g`, italic `g.a`. Match Office Code Pro's
  x-height and italic angle, and keep the 600-unit advance.
- Use Ligaturizer's API without modifying cloned source repositories.
  Select Fira Code by weight explicitly, including for italic styles.
- Keep the ligature exclusions: `&&`, `~@`, `\/`, `.?`, `?:`, `?=`,
  `?.`, `??`, `;;`, `/\`. The bundled Fira Code also lacks `~=`.
- Programming ligatures use `calt`. Export OpenType layout without `morx`,
  `mort`, or `feat`: Offlig D's competing AAT table disables its ligatures.
- Run `make check` after changes to font generation. It validates outlines,
  names, style flags, cell widths, feature switches, and actual shaping using
  HarfBuzz and CoreText when available.
- `make` builds and validates. `make build` keeps source clones and rebuilds
  when inputs change. `make clean` removes only this project's outputs.
- Keep upstream copyright/license notices with the generated fonts.
- Respect existing changes; never reset or revert unless explicitly told.
- Prefer fast read/search tools (`rg`, `rg --files`); avoid destructive commands.
- Use `apply_patch` for edits; keep ASCII; add comments only when clarifying
  non-obvious logic.
- Follow sandbox/approval rules; request escalation when network or restricted
  paths are required.
- No heavy formatting in replies; reference files with clickable code paths.
- When automating, include validation or assertions where practical; summarize
  key outcomes succinctly.
