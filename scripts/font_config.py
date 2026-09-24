"""Shared inputs and feature policy for Ergonomic Mono."""

import sys
from pathlib import Path


FAMILY = "Ergonomic Mono"
POSTSCRIPT_FAMILY = "ErgonomicMono"
STYLES = {
    "Light": (300, "Light"),
    "LightItalic": (300, "LightIt"),
    "Regular": (400, "Regular"),
    "RegularItalic": (400, "It"),
    "Medium": (500, "Medium"),
    "MediumItalic": (500, "MediumIt"),
    "Bold": (700, "Bold"),
    "BoldItalic": (700, "BoldIt"),
}
EXCLUDED_LIGATURES = frozenset(
    ("&&", "~@", "\\/", ".?", "?:", "?=", "?.", "??", ";;", "/\\")
)
# The Fira Code revision pinned by Ligaturizer does not contain this glyph.
MISSING_FIRA_LIGATURES = frozenset(("~=",))


def load_ligatures(directory):
    sys.path.insert(0, str(Path(directory).resolve()))
    from char_dict import char_dict
    from ligatures import ligatures

    specs = {
        "".join(char_dict[char] for char in spec["chars"]): spec
        for spec in ligatures
        if spec["firacode_ligature_name"] is not None
    }
    missing = EXCLUDED_LIGATURES - specs.keys()
    if missing:
        raise ValueError("Ligaturizer's exclusion list changed: %s" % sorted(missing))
    return {text: spec for text, spec in specs.items() if text not in EXCLUDED_LIGATURES}


def style_names(style):
    weight = style.removesuffix("Italic")
    italic = style.endswith("Italic")
    preferred = (weight + (" Italic" if italic else "")).replace("Regular Italic", "Italic")
    legacy_family = FAMILY if weight in ("Regular", "Bold") else FAMILY + " " + weight
    legacy_style = "Bold" if weight == "Bold" else "Regular"
    if italic:
        legacy_style = "Bold Italic" if weight == "Bold" else "Italic"
    return preferred, legacy_family, legacy_style
