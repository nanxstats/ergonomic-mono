#!/usr/bin/env python3
"""Validate generated outlines, metadata and actual HarfBuzz/CoreText shaping."""

import argparse
import json
from pathlib import Path
import shutil
import struct
import subprocess

import fontforge

from font_config import EXCLUDED_LIGATURES, FAMILY, POSTSCRIPT_FAMILY, STYLES
from font_config import MISSING_FIRA_LIGATURES, load_ligatures, style_names


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def read_tables(path):
    data = path.read_bytes()
    count = struct.unpack_from(">H", data, 4)[0]
    tables = {}
    for index in range(count):
        tag, _, offset, length = struct.unpack_from(">4sIII", data, 12 + 16 * index)
        tables[tag.decode("ascii")] = data[offset:offset + length]
    return tables


def validate_metadata(path, font, style):
    tables = read_tables(path)
    require({"GSUB", "GDEF", "CFF "} <= tables.keys(), "Missing OpenType tables")
    require(not {"morx", "mort", "feat"} & tables.keys(), "Unexpected AAT layout tables")
    require(struct.unpack_from(">I", tables["post"], 12)[0] == 1, "Not marked fixed pitch")
    italic, bold = style.endswith("Italic"), style.startswith("Bold")
    require(struct.unpack_from(">H", tables["head"], 44)[0] & 3 == bold + 2 * italic,
            "Incorrect macStyle bold/italic bits")
    require(font.os2_weight == STYLES[style][0], "Incorrect weight class")
    expected_selection = int(italic) + 32 * bold
    require(font.os2_stylemap & 97 == (expected_selection or 64), "Incorrect fsSelection bits")
    require(font.italicangle == (-9 if italic else 0), "Incorrect italic angle")
    preferred, legacy_family, legacy_style = style_names(style)
    expected = {
        1: legacy_family, 2: legacy_style, 4: FAMILY + " " + preferred,
        6: POSTSCRIPT_FAMILY + "-" + style, 16: FAMILY, 17: preferred,
    }
    name = tables["name"]
    _, count, strings = struct.unpack_from(">HHH", name)
    found = set()
    for index in range(count):
        platform, _, _, name_id, length, offset = struct.unpack_from(">6H", name, 6 + 12 * index)
        if name_id not in expected:
            continue
        value = name[strings + offset:strings + offset + length]
        value = value.decode("utf-16-be" if platform in (0, 3) else "mac_roman")
        require(value == expected[name_id], "Incorrect name ID %d: %s" % (name_id, value))
        found.add(name_id)
    require(found == expected.keys(), "Missing family/style names")
    features = {
        feature
        for lookup in font.gsub_lookups
        for feature, _ in font.getLookupInfo(lookup)[2]
    }
    require({"calt", "ss01", "ss02"} <= features, "Missing required features")
    coverage = {}
    for lookup in font.gsub_lookups:
        for feature, scripts in font.getLookupInfo(lookup)[2]:
            for script, languages in scripts:
                coverage.setdefault(feature, set()).update((script, lang) for lang in languages)
    for feature in ("ss01", "ss02"):
        require(coverage["calt"] <= coverage[feature], "Variant unavailable in some script/language: " + feature)
    labels = {tag: label for _, tag, label in font.style_set_names}
    require(labels.get("ss01") == "Dotted zero", "Missing ss01 label")
    require(labels.get("ss02") == "Double-storey g", "Missing ss02 label")


def validate_outlines(font, source, donor, style):
    require(font.em == source.em == 1000, "Unexpected units per em")
    require(font["space"].width == 600, "Unexpected cell width")
    for glyph in font.glyphs():
        require(glyph.width in (0, 600), "Non-monospace glyph: " + glyph.glyphname)
        if glyph.glyphname.startswith("lig."):
            require(len(glyph.foreground) > 0 and glyph.boundingBox()[0] < 0,
                    "Empty or incorrectly positioned ligature: " + glyph.glyphname)
        if glyph.glyphname.startswith("CR."):
            require(len(glyph.foreground) == 0, "Ligature spacer has a visible outline")
    for original in source.glyphs():
        if original.unicode >= 0:
            require(original.unicode in font, "Lost character U+%04X" % original.unicode)
    for name in ("zero", "zero.alt", "g", "x", "ampersand", "question", "less", "greater"):
        require(font[name].foreground == source[name].foreground, "Changed source outline: " + name)
    require(font["zero"].foreground != font["zero.alt"].foreground, "Identical zero variants")
    require(font["g"].foreground != font["g.ss02"].foreground, "Identical g variants")
    donor_g = donor["g.a" if style.endswith("Italic") else "g"]
    require(len(font["g.ss02"].foreground) == len(donor_g.foreground), "Lost donor contours")
    height_scale = source["x"].boundingBox()[3] / donor["x"].boundingBox()[3]
    bounds = font["g.ss02"].boundingBox()
    donor_bounds = donor_g.boundingBox()
    for index in (1, 3):
        require(abs(bounds[index] - donor_bounds[index] * height_scale) <= 1,
                "Incorrect donor height/descender scaling")
    require(bounds[1] >= -font.os2_windescent and bounds[3] <= font.os2_winascent,
            "Alternate g exceeds vertical metrics")


def shape(hb_shape, path, texts, features, shaper, script=None, language=None):
    command = [hb_shape, str(path), "--text-file=-", "--output-format=json",
               "--features=" + features, "--shapers=" + shaper]
    if script:
        command.append("--script=" + script)
    if language:
        command.append("--language=" + language)
    result = subprocess.run(command, input="\n".join(texts) + "\n", text=True,
                            capture_output=True, check=True)
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    require(len(rows) == len(texts), "HarfBuzz returned the wrong number of results")
    for text, row in zip(texts, rows):
        require(len(row) == len(text), "Changed cell count: " + repr(text))
        require(all(abs(g["ax"] - 600) < 0.01 and g["ay"] == 0 for g in row),
                "Changed cell advance: " + repr(text))
        require(all(g["dx"] == g["dy"] == 0 for g in row), "Unexpected positioning: " + repr(text))
    return [[g["g"] for g in row] for row in rows]


def validate_shaping(hb_shape, path, texts, shapers):
    excluded = sorted(EXCLUDED_LIGATURES)
    samples = texts + excluded
    for shaper in shapers:
        for script in ("latn", "zyyy"):
            off = shape(hb_shape, path, samples, "calt=0,liga=0", shaper, script)
            on = shape(hb_shape, path, samples, "calt=1,liga=1", shaper, script)
            for text, normal, ligature in zip(texts, off, on):
                require(normal != ligature and ligature[-1].startswith("lig."),
                        "%s/%s: ligature failed for %r" % (shaper, script, text))
                require(all(g.startswith("CR.") for g in ligature[:-1]),
                        "Incomplete contextual substitution: " + repr(text))
            require(off[len(texts):] == on[len(texts):], "An excluded ligature was enabled")
        for dotted in (0, 1):
            for double in (0, 1):
                features = "ss01=%d,ss02=%d,calt=1,liga=1" % (dotted, double)
                row = shape(hb_shape, path, ["0g ->"], features, shaper)[0]
                require(row[:2] == ["zero.alt" if dotted else "zero", "g.ss02" if double else "g"],
                        "Glyph feature switches failed: " + features)
                require(row[-1].startswith("lig."), "Variants interfered with calt")
                row = shape(hb_shape, path, ["0g ->"], features + ",calt=0,liga=0", shaper)[0]
                require(row[:2] == ["zero.alt" if dotted else "zero", "g.ss02" if double else "g"],
                        "Glyph variants depend on ligatures")
                require(row[-2:] == ["hyphen", "greater"], "calt=0 failed to disable ligatures")
        default = shape(hb_shape, path, ["0g ->"], "", shaper)[0]
        require(default[:2] == ["zero", "g"] and default[-1].startswith("lig."),
                "Incorrect default glyphs or ligatures")
        liga_only = shape(hb_shape, path, ["->"], "calt=0,liga=1", shaper)[0]
        require(liga_only == ["hyphen", "greater"], "Unexpected liga-only substitution")
        for language in ("ca", "es", "ro", "tr", "sr"):
            row = shape(hb_shape, path, ["0g ->"], "ss01=1,ss02=1,calt=1", shaper,
                        script="latn", language=language)[0]
            require(row[:2] == ["zero.alt", "g.ss02"] and row[-1].startswith("lig."),
                    "Features unavailable for language: " + language)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hb-shape", default="hb-shape")
    parser.add_argument("--office-dir", type=Path, default=Path("Office-Code-Pro"))
    parser.add_argument("--source-dir", type=Path, default=Path("source-code-pro"))
    parser.add_argument("--ligaturizer-dir", type=Path, default=Path("Ligaturizer"))
    parser.add_argument("--output-dir", type=Path, default=Path("fonts"))
    args = parser.parse_args()
    if not shutil.which(args.hb_shape):
        raise SystemExit("Install hb-shape for validation (brew install harfbuzz).")
    available = subprocess.check_output([args.hb_shape, "--list-shapers"], text=True).split()
    shapers = [shaper for shaper in ("ot", "coretext") if shaper in available]
    require("ot" in shapers, "HarfBuzz lacks the OpenType shaper")
    specs = load_ligatures(args.ligaturizer_dir)
    for style in STYLES:
        path = args.output_dir / (POSTSCRIPT_FAMILY + "-" + style + ".otf")
        font = fontforge.open(str(path))
        source_path = args.office_dir / "Fonts/Office Code Pro/OTF" / ("OfficeCodePro-" + style + ".otf")
        source = fontforge.open(str(source_path))
        donor = fontforge.open(str(args.source_dir / "OTF" / ("SourceCodePro-" + STYLES[style][1] + ".otf")))
        weight = style.removesuffix("Italic")
        fira = fontforge.open(str(args.ligaturizer_dir / "fonts/fira/distr/otf" / ("FiraCode-" + weight + ".otf")))
        try:
            missing = {text for text, spec in specs.items() if spec["firacode_ligature_name"] not in fira}
            require(missing <= MISSING_FIRA_LIGATURES, "Unexpected missing donor ligatures")
            texts = sorted(specs.keys() - missing)
            validate_metadata(path, font, style)
            validate_outlines(font, source, donor, style)
            validate_shaping(args.hb_shape, path, texts, shapers)
            print("PASS %s: %d ligatures, 10 exclusions, 4 variant combinations (%s)" % (
                path.name, len(texts), ", ".join(shapers)
            ))
        finally:
            font.close()
            source.close()
            donor.close()
            fira.close()


if __name__ == "__main__":
    main()
