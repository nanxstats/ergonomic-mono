# Backtick spacing investigation

## Cause

The upstream Office Code Pro Light, Light Italic, Bold, and Bold Italic OTFs
classify eleven spacing accents as `GDEF` class 3 (mark), including U+0060
`grave`, the ASCII backtick. Their horizontal advance is already 600 units.
The same incorrect classifications were inherited by Ergonomic Mono.

The [OpenType GDEF specification](https://learn.microsoft.com/en-us/typography/opentype/spec/gdef#glyph-class-definition-table)
defines class 1 as a spacing base glyph and class 3 as a nonspacing combining
mark. HarfBuzz's
[`zero_mark_widths_by_gdef`](https://github.com/harfbuzz/harfbuzz/blob/main/src/hb-ot-shape.cc)
zeros advances for glyphs classified as marks. Both HarfBuzz's OpenType shaper
and CoreText reproduce the lost backtick advances in these fonts.

The affected glyphs are `grave`, `dieresis`, `macron`, `acute`, `cedilla`,
`circumflex`, `caron`, `breve`, `dotaccent`, `ring`, and `tilde`. They are
Unicode spacing symbols or modifier letters, distinct from the U+0300-series
combining marks. The ASCII caret and tilde are separate, unaffected glyphs.

Regular and Medium, including their italics, have a different upstream layout:
their source OTFs contain `morx`/`feat` instead of `GDEF`/`GPOS`/`GSUB`.
The generated OpenType fonts do not classify their spacing accents as marks,
which explains the weight-specific behavior. Italic angle and Fira Code
ligature weight selection are not the cause.

## Reproduction and isolation

The literal text below contains 18 characters and should advance 10800 units
(18 cells of 600 units):

````text
**`example.json`**
````

| Styles (upright and italic) | Before | After |
| --- | --- | --- |
| Light, Bold | 9600 units; each backtick advances 0 | 10800 units; each backtick advances 600 |
| Regular, Medium | 10800 units | 10800 units |

Both shapers give these results. The failure also occurs in the unmodified
upstream fonts and with `calt=0,liga=0` or `mark=0,mkmk=0`. Disabling those
features does not change the glyph classification. The backticks occupy no
cell, so they overlap adjacent characters and shorten the line by two cells.

Changing only the eleven `GDEF` class entries from 3 to 1 in temporary copies
fixes the example in both shapers. This isolates the classification error
without changing outlines, metrics, or substitution/positioning rules.

To inspect the rebuilt font directly:

```sh
hb-shape fonts/ErgonomicMono-Bold.otf \
  --text='**`example.json`**' --shapers=ot --output-format=json
hb-shape fonts/ErgonomicMono-Bold.otf \
  --text='**`example.json`**' --shapers=coretext --output-format=json
```

Every output glyph should have `ax=600`, `ay=0`, `dx=0`, and `dy=0`.
CoreText is available on macOS builds of HarfBuzz.

## Repair and regression coverage

The build repairs encoded glyphs incorrectly classified as marks when their
Unicode general category is not a mark (`M`). It explicitly sets FontForge's
`glyphclass` to `baseglyph` before OpenType export. It does not infer mark
status from width: the upstream genuine combining marks also have 600-unit
horizontal metrics. Unencoded glyphs and genuine combining marks retain their
existing classifications, outlines, metrics, and anchors. Source clones are
unchanged.

The regression checks reject spacing characters classified as marks and
verify the original ASCII, spacing-accent, and combining-mark outlines and
metrics. Combining mark classes and anchors are checked against the source.
Shaping covers the reported Markdown string, repeated backticks, every
printable ASCII character alone and around a backtick, and all eleven spacing
accents alone and in context. These checks run for all eight styles, Latin and
common script, default features and ligatures on/off, using HarfBuzz and
CoreText when available.

The new checks fail on the original four affected styles and pass on the
original Regular/Medium styles. After the repair, `make check` passes in both
shapers for all eight styles, including the existing 127 ligatures, ten
exclusions, four variant combinations, metadata, and outline checks.

A binary comparison against the fonts saved before rebuilding confirms that
only `GDEF` and the `head` table differ in Light/Bold; Regular/Medium differ
only in `head`. All outline, metric, substitution, and positioning tables are
identical. Shaping all thirteen supported combining accents after `x`, stacked
grave/acute marks, and a decomposed accented letter also gives identical
before/after results in each engine. This checks preservation of existing
combining behavior in each style and engine.
