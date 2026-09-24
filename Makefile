SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c
.DEFAULT_GOAL := all
.DELETE_ON_ERROR:

FONTFORGE ?= fontforge
HB_SHAPE ?= hb-shape
LIGATURIZER_DIR := Ligaturizer
OFFICE_DIR := Office-Code-Pro
SOURCE_DIR := source-code-pro
OUTPUT_DIR := fonts

STYLES := Light LightItalic Regular RegularItalic Medium MediumItalic Bold BoldItalic
DONOR_STYLES := Light LightIt Regular It Medium MediumIt Bold BoldIt
FIRA_WEIGHTS := Light Regular Medium Bold
OFFICE_OTF_DIR := $(OFFICE_DIR)/Fonts/Office\ Code\ Pro/OTF
SOURCE_FONTS := $(addprefix $(OFFICE_OTF_DIR)/OfficeCodePro-,$(addsuffix .otf,$(STYLES)))
DONOR_FONTS := $(addprefix $(SOURCE_DIR)/OTF/SourceCodePro-,$(addsuffix .otf,$(DONOR_STYLES)))
FIRA_FONTS := $(addprefix $(LIGATURIZER_DIR)/fonts/fira/distr/otf/FiraCode-,$(addsuffix .otf,$(FIRA_WEIGHTS)))
LIGATURIZER_SCRIPTS := $(addprefix $(LIGATURIZER_DIR)/,ligaturize.py ligatures.py char_dict.py)
FINAL_FONTS := $(addprefix $(OUTPUT_DIR)/ErgonomicMono-,$(addsuffix .otf,$(STYLES)))
LICENSES := $(addprefix $(OUTPUT_DIR)/,OFL-Office-Code-Pro.txt OFL-Source-Code-Pro.txt OFL-Fira-Code.txt)

.PHONY: all build check deps sources clean

all: check

build: $(FINAL_FONTS) $(LICENSES)

check: build
	$(FONTFORGE) -skippyfile -skippyplug -lang=py -script scripts/validate_fonts.py --hb-shape "$(HB_SHAPE)" \
		--office-dir "$(OFFICE_DIR)" --source-dir "$(SOURCE_DIR)" \
		--ligaturizer-dir "$(LIGATURIZER_DIR)" --output-dir "$(OUTPUT_DIR)"

deps:
	@command -v "$(FONTFORGE)" >/dev/null || { echo "Install FontForge (brew install fontforge)." >&2; exit 1; }

sources: $(SOURCE_FONTS) $(DONOR_FONTS) $(FIRA_FONTS) $(LIGATURIZER_SCRIPTS)

$(OUTPUT_DIR):
	mkdir -p "$@"

$(OFFICE_DIR)/.git:
	git clone https://github.com/phooky/Office-Code-Pro.git "$(OFFICE_DIR)"

$(SOURCE_DIR)/.git:
	git clone --depth 1 --branch release https://github.com/adobe-fonts/source-code-pro.git "$(SOURCE_DIR)"

$(LIGATURIZER_DIR)/.git:
	git clone https://github.com/ToxicFrog/Ligaturizer.git "$(LIGATURIZER_DIR)"

$(LIGATURIZER_DIR)/fonts/fira/.git: | $(LIGATURIZER_DIR)/.git
	git -C "$(LIGATURIZER_DIR)" submodule update --init --depth 1 fonts/fira

$(SOURCE_FONTS) $(OFFICE_DIR)/LICENSE.txt: | $(OFFICE_DIR)/.git
	@test -f "$@"

$(DONOR_FONTS) $(SOURCE_DIR)/LICENSE.md: | $(SOURCE_DIR)/.git
	@test -f "$@"

$(LIGATURIZER_SCRIPTS): | $(LIGATURIZER_DIR)/.git
	@test -f "$@"

$(FIRA_FONTS) $(LIGATURIZER_DIR)/fonts/fira/LICENSE: | $(LIGATURIZER_DIR)/fonts/fira/.git
	@test -f "$@"

$(FINAL_FONTS): $(OUTPUT_DIR)/ErgonomicMono-%.otf: Makefile scripts/build_font.py scripts/font_config.py $(SOURCE_FONTS) $(DONOR_FONTS) $(FIRA_FONTS) $(LIGATURIZER_SCRIPTS) | deps $(OUTPUT_DIR)
	$(FONTFORGE) -skippyfile -skippyplug -lang=py -script scripts/build_font.py --style "$*" \
		--office-dir "$(OFFICE_DIR)" --source-dir "$(SOURCE_DIR)" \
		--ligaturizer-dir "$(LIGATURIZER_DIR)" --output "$@" \
		2>&1 | sed '/^This contextual rule applies no lookups\.$$/d'

$(OUTPUT_DIR)/OFL-Office-Code-Pro.txt: $(OFFICE_DIR)/LICENSE.txt | $(OUTPUT_DIR)
	cp "$<" "$@"

$(OUTPUT_DIR)/OFL-Source-Code-Pro.txt: $(SOURCE_DIR)/LICENSE.md | $(OUTPUT_DIR)
	cp "$<" "$@"

$(OUTPUT_DIR)/OFL-Fira-Code.txt: $(LIGATURIZER_DIR)/fonts/fira/LICENSE | $(OUTPUT_DIR)
	cp "$<" "$@"

clean:
	rm -f $(FINAL_FONTS) $(LICENSES)
