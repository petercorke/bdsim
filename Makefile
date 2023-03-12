.FORCE:

BLUE=\033[0;34m
BLACK=\033[0;30m

help:
	@echo "$(BLUE) make test - run all unit tests"
	@echo " make coverage - run unit tests and coverage report"
	@echo " make docs - build Sphinx documentation"
	@echo " make docupdate - upload Sphinx documentation to GitHub pages"
	@echo " make dist - build dist files"
	@echo " make upload - upload to PyPI"
	@echo " make clean - remove dist and docs build files"
	@echo " make help - this message$(BLACK)"

test:
	pytest

coverage:
	pytest --cov=bdsim
	coverage report

docs: .FORCE
	(cd docs; make html)

view:
	open docs/build/html/index.html

dist: .FORCE
	#$(MAKE) test
	python -m build

upload: .FORCE
	twine upload dist/*

install:
	pip install -e .

clean: .FORCE
	# (cd docsrc; make clean)
	-rm -r *.egg-info
	-rm -r dist build
