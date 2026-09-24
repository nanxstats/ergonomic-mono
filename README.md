# Ergonomic Mono

A customizable coding font with selectable glyph variants and programming ligatures.

Derived from [phooky's fork of Office Code Pro](https://github.com/phooky/Office-Code-Pro),
patched with [Fira Code](https://github.com/tonsky/FiraCode) programming
ligatures using [Ligaturizer](https://github.com/ToxicFrog/Ligaturizer),
plus selectable zero and lowercase g variants.
Each style contains both zero and g variants; there are no separate dotted zero
font files.

![Ergonomic Mono in Ghostty. With Ghostty configuration `adjust-cell-height = 8`. Theme: Raycast Dark.](documentation/screenshot-ghostty.png)

## Install

Install with Homebrew:

```bash
brew install --cask nanxstats/tap/font-ergonomic-mono
```

Or install the `fonts/ErgonomicMono-*.otf` files using your OS font manager.

## Configure

Select **Ergonomic Mono** in your editor or terminal.
Restart the application after installing or replacing fonts.

| Feature | Disabled | Enabled |
| --- | --- | --- |
| `ss01` | Slashed zero (default) | Dotted zero |
| `ss02` | Single-storey g (default) | Double-storey g |
| `calt` | Separate operators | Programming ligatures (normally enabled) |

These features are independent. For example, enable `ss02` for a double-storey
g while keeping the slashed zero. The g switch changes U+0067; precomposed
accented g characters retain their original designs. Applications must support
OpenType feature settings to select alternates.

Programming ligatures use `calt`; enabling `liga` alone does not activate them.
Set `calt=0` to disable ligatures while retaining your zero and g preferences.

Open [the local specimen](documentation/specimen.html) in a browser to compare
all eight styles and toggle the features without installing the fonts.

### VS Code

In `settings.json`, this example enables ligatures, dotted zero, and
double-storey g in both the editor and integrated terminal:

```json
{
  "editor.fontFamily": "'Ergonomic Mono', monospace",
  "editor.fontLigatures": "'calt', 'liga', 'ss01', 'ss02'",
  "terminal.integrated.fontFamily": "'Ergonomic Mono', monospace",
  "terminal.integrated.fontLigatures.enabled": true,
  "terminal.integrated.fontLigatures.featureSettings": "'calt', 'liga', 'ss01', 'ss02'"
}
```

Remove `'ss01'` for slashed zero; remove `'ss02'` for single-storey g.
See [VS Code's terminal ligature settings](https://code.visualstudio.com/docs/terminal/appearance#_ligatures).

### Ghostty

```ini
font-family = Ergonomic Mono
font-feature = ss01, ss02
```

Remove the `ss01` or `ss02` line to restore the default glyph.
See [Ghostty's font feature syntax](https://ghostty.org/docs/config/reference#font-feature).

## Build

Requirements: Git, Make, FontForge with Python 3.9+ support, and HarfBuzz's
`hb-shape` for validation. On macOS, these are available through Homebrew:

```sh
brew install fontforge harfbuzz
make
```

`make` builds and validates the fonts. Other targets:

- `make build`: generate the eight fonts and copy their upstream licenses.
- `make check`: build if needed, then validate the generated fonts.
- `make sources`: fetch or verify the source fonts and Ligaturizer.
- `make clean`: remove only this project's eight generated fonts and license
  copies. Source clones and unrelated files are retained.

A populated checkout builds offline. Missing dependencies are cloned over HTTPS:

| Directory | Repository / branch |
| --- | --- |
| `Office-Code-Pro/` | `phooky/Office-Code-Pro`, default branch |
| `source-code-pro/` | `adobe-fonts/source-code-pro`, `release` branch (contains OTFs) |
| `Ligaturizer/` | `ToxicFrog/Ligaturizer`, default branch |
| `Ligaturizer/fonts/fira/` | Fira Code submodule at Ligaturizer's recorded commit |

Existing clones are reused without pulling, resetting, patching, or deleting
them. Only the Fira Code submodule is initialized; the other Ligaturizer
submodules are unnecessary.

The build uses these inputs:

- Slashed zero Office Code Pro OTFs in
  `Office-Code-Pro/Fonts/Office Code Pro/OTF/`.
- The embedded `zero.alt` glyph, which matches the corresponding Office Code
  Pro D dotted zero. The D fonts are not needed for the build.
- Matching Source Code Pro weights in `source-code-pro/OTF/`. Uprights use
  `g`; italics use the double-storey `g.a` alternate. Each donor is scaled
  to the target x-height, adjusted from Source Code Pro's 11-degree italic
  slant to Office Code Pro's 9-degree slant, and kept at a 600-unit advance.
- Matching Fira Code Light, Regular, Medium, and Bold OTFs, including for italic
  styles. Ligature outlines retain Fira Code's upright design.

[scripts/build_font.py](scripts/build_font.py) calls Ligaturizer's
`LigatureCreator` directly. This replaces the old edits to `prefixed_fonts`
and `renamed_fonts` in the cloned `build.py`. The driver filters ligatures in
memory, preserves Office Code Pro's ordinary punctuation, adds labeled
`ss01`/`ss02` features, and writes consistent names and bold/italic metadata.
The output explicitly uses OpenType layout tables and omits inherited Apple
AAT layout tables.

The generated files are:

| Weight | Upright | Italic |
| --- | --- | --- |
| Light | `ErgonomicMono-Light.otf` | `ErgonomicMono-LightItalic.otf` |
| Regular | `ErgonomicMono-Regular.otf` | `ErgonomicMono-RegularItalic.otf` |
| Medium | `ErgonomicMono-Medium.otf` | `ErgonomicMono-MediumItalic.otf` |
| Bold | `ErgonomicMono-Bold.otf` | `ErgonomicMono-BoldItalic.otf` |

All output files land in `fonts/`. Every style belongs to the preferred family
`Ergonomic Mono`; Light and Medium also have legacy weight-specific family
names for applications that only support four-style families.

### Ligature selection and validation

These ligatures from Fira Code are intentionally omitted:

`&&`, `~@`, `\/`, `.?`, `?:`, `?=`, `?.`, `??`, `;;`, `/\`

The bundled Fira Code revision also lacks the glyph for `~=`, so it remains
unligated. This produces 127 programming ligatures per style. Other missing
ligature glyphs cause a build failure.

[scripts/validate_fonts.py](scripts/validate_fonts.py) checks:

- All retained ligatures with `calt` on and off, for Latin and common-script text.
- Every exclusion and all four combinations of zero/g features.
- Feature independence, default behavior, cell counts, and 600-unit advances.
- Preserved source outlines and character coverage, visible ligature outlines,
  donor g height, font naming, style flags, and the absence of AAT layout tables.

Validation uses HarfBuzz's OpenType shaper and also CoreText when available.
The checked source revisions were Office Code Pro `d8fe9b1`, Source Code Pro
`803b7e2`, Ligaturizer `c406518`, and its Fira Code submodule `e9943d2`.
Future fresh clones may contain different revisions.

## License

The generated fonts are under the SIL Open Font License 1.1. The build copies
Office Code Pro, Source Code Pro, and Fira Code copyright/license notices into
`fonts/OFL-*.txt`; keep those files with any redistributed fonts. The root
[LICENSE](LICENSE) contains the OFL text.
