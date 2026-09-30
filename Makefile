.PHONY: all raw model tmdl previews
all: raw model tmdl previews
raw:
	python generator/generate_raw.py
model:
	python generator/build_model.py
tmdl:
	python generator/build_tmdl.py
previews:
	python generator/make_previews.py
