.PHONY: build install clean

build:
	bash scripts/build.sh

clean:
	rm -rf build dist __pycache__ payu_cli/__pycache__ payu_cli/commands/__pycache__
