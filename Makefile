all: build

.PHONY: setup
setup:
	python3.10 -m venv venv
	./venv/bin/python -m pip install --upgrade build
	./venv/bin/python -m pip install --upgrade twine

.PHONY: build
build:
	./venv/bin/python -m build

.PHONY: install
install:
	python -m pip install dist/h2ogpte_mcp_server-*.whl

.PHONY: uninstall
uninstall:
	python -m pip uninstall h2ogpte_mcp_server

.PHONY: upload
upload:
	./venv/bin/python -m twine upload dist/*.whl

.PHONY: clean
clean:
	rm -rf dist build