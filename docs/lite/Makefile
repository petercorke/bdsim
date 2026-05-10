BDSIM_ROOT := $(abspath ../..)
OUTDIR     := ../build/html/lite
PORT       := 8888

BLUE=\033[0;34m
BLACK=\033[0;30m

.PHONY: help go build serve clean notebook wheel dev distclean

help:
	@echo "$(BLUE) make go        - copy notebook, build site, start server (do everything)"
	@echo " make notebook  - copy and adapt bouncing-ball.ipynb from examples/ for Pyodide"
	@echo " make wheel     - build local dev wheel + piplite index (overrides PyPI)"
	@echo " make build     - build JupyterLite site into $(OUTDIR)"
	@echo " make dev       - wheel + build only (use 'make wheel go' to also serve)"
	@echo " make serve     - build then serve on http://localhost:$(PORT)/lite/"
	@echo " make clean     - remove built site (keeps pypi/ and files/)"
	@echo " make distclean - clean + remove built wheels"
	@echo " make help      - this message$(BLACK)"

## Do everything: copy notebook, build site, start server
go: notebook build
	mkdir -p $(OUTDIR)/files
	cp ../notebooks/bouncing-ball.ipynb $(OUTDIR)/files/bouncing-ball.ipynb
	cp reset.html ../build/html/reset.html
	-lsof -ti tcp:$(PORT) | xargs kill -9 2>/dev/null
	python3 serve.py $(PORT) ../build/html &
	sleep 0.5
	open "http://localhost:$(PORT)/reset.html"

## Copy and adapt the notebook from examples/ (run before first build, or when source changes)
notebook:
	cp $(BDSIM_ROOT)/examples/bouncing-ball.ipynb ../notebooks/bouncing-ball.ipynb
	python3 adapt_nb.py

## Build the JupyterLite site into $(OUTDIR)
build: notebook
	jupyter lite build --output-dir $(OUTDIR) --contents ../notebooks --force

## Build wheel for local pypi and regenerate the piplite index
wheel:
	pip install --quiet build
	rm -f pypi/*.whl
	python3 -m build --wheel --outdir pypi $(BDSIM_ROOT)
	python3 gen_index.py

## Full dev rebuild: wheel + site (use this when you change bdsim source)
dev: wheel build

## Serve the built site on http://localhost:$(PORT)
serve: build
	cp reset.html ../build/html/reset.html
	-lsof -ti tcp:$(PORT) | xargs kill -9 2>/dev/null
	python3 serve.py $(PORT) ../build/html &
	sleep 0.5
	open "http://localhost:$(PORT)/reset.html"

## Remove build artefacts (keeps pypi/ and files/ intact)
clean:
	rm -rf $(OUTDIR)

## Remove everything including the built wheel cache
distclean: clean
	rm -rf pypi/*.whl pypi/all.json
