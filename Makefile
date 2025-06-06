all: build

.PHONY: setup
setup:
	python3.10 -m venv venv
	./venv/bin/python -m pip install --upgrade build
	./venv/bin/python -m pip install --upgrade twine

.PHONY: build
build:
	./venv/bin/python -m build

.PHONY: upload
upload:
	./venv/bin/python -m twine upload dist/*

.PHONY: clean
clean:
	rm -rf dist build