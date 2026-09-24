# Offlig ligature investigation

## Summary

The Offlig D fonts contain both `morx` (Apple AAT substitutions) and `GSUB`
(OpenType substitutions). Their programming ligatures are in `GSUB`,
but the competing `morx` table prevents them from taking effect in the tested
HarfBuzz and CoreText shapers. Removing only `morx` from temporary copies
restores ligatures in all eight dotted zero styles. This is consistent with
[HarfBuzz's documented table precedence](https://harfbuzz.github.io/shaping-and-shape-plans.html).

The slashed zero Offlig fonts already shape correctly in those direct tests.
The dotted zero Offlig fonts have a reproducible layout table conflict.
All eight Offlig D OTFs contain both `morx` and `GSUB`. Their programming
ligatures are in `GSUB`, but shaping uses the competing AAT substitutions.
The slashed Offlig fonts do not contain `morx` and their programming ligatures work.

## Direct shaping results

Test string: `-> => != === <= &&`, with `calt=1,liga=1`. Each row covers Light,
Regular, Medium, Bold, and their italic companions.

| Font files | HarfBuzz `ot` | CoreText |
| --- | --- | --- |
| Original slashed zero Offlig (8) | 6/6 ligatures | 6/6 ligatures |
| Original dotted zero Offlig D (8) | 0/6 ligatures | 0/6 ligatures |
| Temporary Offlig D copies with only `morx` removed (8) | 6/6 ligatures | 6/6 ligatures |

Removing only `morx` is sufficient to restore the six tested ligatures in every
dotted zero style. The original clones were not modified. All shaped glyphs
retain a 600-unit advance. Disabling `calt` disables the programming ligatures;
`liga` alone does not enable them.

HarfBuzz's `ot` shaper also supports AAT: selecting `--shapers=ot` does not force
it to ignore `morx`. Its [documented table precedence](https://harfbuzz.github.io/shaping-and-shape-plans.html)
explains why the presence of valid `GSUB` rules is insufficient here.

To reproduce the original failure and the working slashed font:

```sh
hb-shape 'Offlig/Dotted Zero/OffligD-Regular.otf' \
  --text='-> => != === <= &&' --features='calt=1,liga=1' --shapers=ot
hb-shape 'Offlig/Slashed Zero/Offlig-Regular.otf' \
  --text='-> => != === <= &&' --features='calt=1,liga=1' --shapers=ot
```

The first result uses ordinary names such as `hyphen` and `greater`. The second
uses `CR.*` spacers and `lig.*` glyphs. Repeat with `--shapers=coretext` on macOS.

For an isolated repair experiment, FontTools' `ttx` can make a temporary copy:

```sh
ttx -x morx -o /tmp/OffligD-Regular-without-morx.ttx \
  'Offlig/Dotted Zero/OffligD-Regular.otf'
ttx -o /tmp/OffligD-Regular-without-morx.otf \
  /tmp/OffligD-Regular-without-morx.ttx
hb-shape /tmp/OffligD-Regular-without-morx.otf \
  --text='-> => != === <= &&' --features='calt=1,liga=1' --shapers=ot
```

## Other observed metadata issues

- Every Offlig style has `OS/2.fsSelection=64` and `head.macStyle=0`, including
  bold and italic fonts. These flags identify all faces as regular upright.
- The slashed fonts share legacy family `Offlig` and subfamily `Regular` even
  across weights and italics. Some preferred style names distinguish the
  faces, but the legacy records do not.
- `Offlig-Regular.otf` still has full name `Office Code Pro`, even though its
  PostScript name is `Offlig-Regular`.

These are additional font-selection concerns, not necessary to reproduce the
dotted zero failure. Direct file shaping does not test an editor's font cache,
installed-font matching, or terminal rendering configuration. A failure of the
slashed zero Offlig family in a particular application remains unconfirmed.

## New build behavior

Ergonomic Mono exports OpenType layout explicitly, omits AAT tables, corrects
names and style flags, and selects the Fira Code donor by weight for both
uprights and italics. It offers both zeros in the same file through `ss01`.

`make check` rejects outputs with `morx`, `mort`, or `feat`; verifies the actual
binary name/style records; and shapes every retained ligature and every
excluded sequence in all eight new fonts. Both OpenType and CoreText are
checked when available, including all zero/g feature combinations.
