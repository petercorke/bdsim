.FORCE:

BLUE=\033[0;34m
BLACK=\033[0;30m

help:
	@echo "$(BLUE) make test - run all unit tests"
	@echo " make coverage - run unit tests and coverage report"
	@echo " make typehints - run mypy type-hint coverage report and open HTML"
	@echo " make docs - build Sphinx documentation"
	@echo " make docupdate - upload Sphinx documentation to GitHub pages"
	@echo " make dist - build dist files"
	@echo " make upload - upload to PyPI"
	@echo " make clean - remove dist and docs build files"
	@echo " make app   - build bdedit.app bundle and register with macOS Launch Services"
	@echo " make help - this message$(BLACK)"

test:
	pytest

coverage:
	coverage run --source='src/bdsim' -m pytest
	coverage report
	coverage html
	open -a Safari htmlcov/index.html

typehints:
	-mypy src/bdsim --ignore-missing-imports --html-report /tmp/mypy-typehints
	open -a Safari /tmp/mypy-typehints/index.html

docs: .FORCE
	(cd docs; make html)

view:
	open docs/build/html/index.html

dist: .FORCE
	#$(MAKE) -C src/bdweb build
	#$(MAKE) test
	python -m build

upload: .FORCE
	$(eval VERSION := $(shell grep '^version' pyproject.toml | sed 's/version = "\(.*\)"/\1/'))
	@echo "Uploading version $(VERSION) to PyPI"
	twine upload dist/*
	git tag v$(VERSION)
	git push origin v$(VERSION)

install:
	pip install -e .

clean: .FORCE
	# (cd docsrc; make clean)
	$(MAKE) -C src/bdweb clean
	-rm -r *.egg-info
	-rm -r dist build

app: .FORCE
	python src/bdsim/bdedit/make_app.py
	/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f bdedit.app
	@echo "bdedit.app registered with Launch Services"
