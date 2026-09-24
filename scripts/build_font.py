#!/usr/bin/env python3
"""Run with FontForge's Python interpreter; leave upstream clones untouched."""

import argparse
import math
import os
from pathlib import Path
import tempfile

import fontforge
import psMat

from font_config import FAMILY, POSTSCRIPT_FAMILY, STYLES, MISSING_FIRA_LIGATURES
from font_config import load_ligatures, style_names


def add_variant(font, feature, original, alternate):
    lookup = POSTSCRIPT_FAMILY + "." + feature
    languages = {"DFLT": {"dflt"}, "latn": {"dflt"}}
    # A language-specific GSUB record does not inherit its default's features.
    for existing in font.gsub_lookups:
        for _, scripts in font.getLookupInfo(existing)[2]:
            for script, tags in scripts:
                languages.setdefault(script, set()).update(tags)
    scripts = tuple((script, tuple(sorted(tags))) for script, tags in sorted(languages.items()))
    font.addLookup(lookup, "gsub_single", (), ((feature, scripts),))
    font.addLookupSubtable(lookup, lookup + ".sub")
    font[original].addPosSub(lookup + ".sub", alternate)


def add_double_storey_g(font, donor, italic):
    # Source Code Pro's italic double-storey g is an alternate, not its base g.
    donor_name = "g.a" if italic else "g"
    donor.em = font.em
    donor.selection.select(donor_name)
    donor.copy()
    glyph = font.createChar(-1, "g.ss02")
    font.selection.select(glyph.glyphname)
    font.paste()
    glyph.unlinkRef()

    width_scale = font["space"].width / donor["space"].width
    height_scale = font["x"].boundingBox()[3] / donor["x"].boundingBox()[3]
    # Remove the donor slant before scaling, then apply Office Code Pro's slant.
    donor_slant = math.tan(math.radians(-donor.italicangle))
    target_slant = math.tan(math.radians(-font.italicangle))
    shear = target_slant * height_scale - donor_slant * width_scale
    glyph.transform((width_scale, 0, shear, height_scale, 0, 0))
    glyph.width = font["space"].width
    glyph.round()
    glyph.autoHint()
    print("  g: %s, height scale %.4f, slant %.1f degrees" % (
        donor_name, height_scale, font.italicangle
    ))


def set_names(font, style, donor):
    preferred, legacy_family, legacy_style = style_names(style)
    font.familyname = FAMILY
    font.fontname = POSTSCRIPT_FAMILY + "-" + style
    font.fullname = FAMILY + " " + preferred
    font.weight = style.removesuffix("Italic")
    font.os2_weight = STYLES[style][0]
    font.os2_stylemap = (1 if style.endswith("Italic") else 0) | (
        32 if style.startswith("Bold") else 0
    )
    if not font.os2_stylemap:
        font.os2_stylemap = 64
    font.copyright = (font.copyright or "") + "\n" + (donor.copyright or "") + (
        "\nProgramming ligatures from Fira Code. "
        "Copyright (c) 2014, The Fira Code Project Authors."
    )
    names = {
        "Family": legacy_family,
        "SubFamily": legacy_style,
        "UniqueID": "1.000;" + POSTSCRIPT_FAMILY + ";" + font.fontname,
        "Fullname": font.fullname,
        "PostScriptName": font.fontname,
        "Preferred Family": FAMILY,
        "Preferred Styles": preferred,
        "Compatible Full": font.fullname,
        "WWS Family": FAMILY,
        "WWS Subfamily": preferred,
        "Copyright": font.copyright,
        "Version": "Version 1.000; Office Code Pro 1.004; Ligaturizer",
    }
    languages = {row[0] for row in font.sfnt_names} | {"English (US)"}
    font.sfnt_names = tuple(row for row in font.sfnt_names if row[1] not in names)
    for language in sorted(languages):
        for key, value in names.items():
            font.appendSFNTName(language, key, value)
    font.version = "1.000"
    font.style_set_names = (
        ("English (US)", "ss01", "Dotted zero"),
        ("English (US)", "ss02", "Double-storey g"),
    )


def normalize_widths(font):
    cell = font["space"].width
    if cell != 600 or font.em != 1000:
        raise ValueError("Unexpected Office Code Pro metrics")
    for glyph in font.glyphs():
        if glyph.unicode >= 0 and glyph.width not in (0, cell):
            glyph.transform(psMat.scale(cell / glyph.width, 1))
            glyph.width = cell
    for glyph in font.glyphs():
        if glyph.width not in (0, cell):
            raise ValueError("Non-monospace glyph: " + glyph.glyphname)


def build(args):
    style = args.style
    weight = style.removesuffix("Italic")
    source = args.office_dir / "Fonts/Office Code Pro/OTF" / ("OfficeCodePro-" + style + ".otf")
    donor_path = args.source_dir / "OTF" / ("SourceCodePro-" + STYLES[style][1] + ".otf")
    fira_path = args.ligaturizer_dir / "fonts/fira/distr/otf" / ("FiraCode-" + weight + ".otf")
    specs = load_ligatures(args.ligaturizer_dir)
    from ligaturize import LigatureCreator

    font = fontforge.open(str(source))
    donor = fontforge.open(str(donor_path))
    fira = fontforge.open(str(fira_path))
    try:
        print("Building " + style)
        for name in ("zero", "zero.alt", "g", "x", "space"):
            if name not in font:
                raise ValueError("Missing source glyph: " + name)
        if font["zero"].foreground == font["zero.alt"].foreground:
            raise ValueError("The slashed and dotted zeros must differ")
        add_double_storey_g(font, donor, style.endswith("Italic"))

        creator = LigatureCreator(font, fira, 0.1, False)
        for text, spec in sorted(specs.items(), key=lambda item: len(item[0])):
            if spec["firacode_ligature_name"] not in fira:
                if text in MISSING_FIRA_LIGATURES:
                    continue
                raise ValueError("Missing Fira Code ligature: " + text)
            creator.add_ligature(spec["chars"], spec["firacode_ligature_name"])
        if creator._lig_counter < len(specs) - len(MISSING_FIRA_LIGATURES):
            raise ValueError("Ligaturizer silently skipped ligatures")
        print("  Added %d contextual ligatures" % creator._lig_counter)
        add_variant(font, "ss01", "zero", "zero.alt")
        add_variant(font, "ss02", "g", "g.ss02")
        set_names(font, style, donor)
        normalize_widths(font)

        # FontForge subtracts underline thickness on export; compensate once.
        font.upos += font.uwidth
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".ergonomic-", dir=args.output.parent) as staging:
            temporary = Path(staging) / args.output.name
            # Do not emit inherited AAT tables that could override GSUB shaping.
            font.generate(str(temporary), flags=("opentype", "round", "no-FFTM-table"))
            os.replace(temporary, args.output)
    finally:
        font.close()
        donor.close()
        fira.close()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--style", choices=STYLES, required=True)
    parser.add_argument("--office-dir", type=Path, default=Path("Office-Code-Pro"))
    parser.add_argument("--source-dir", type=Path, default=Path("source-code-pro"))
    parser.add_argument("--ligaturizer-dir", type=Path, default=Path("Ligaturizer"))
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
