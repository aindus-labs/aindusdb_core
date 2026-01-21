# Makefile for Sphinx documentation
# AindusDB Core Documentation

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD  ?= sphinx-build
SOURCEDIR    = .
BUILDDIR     = _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Install documentation dependencies
install:
	pip install -r requirements.txt

# Build HTML documentation
html:
	@$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)/html" $(SPHINXOPTS) $(O)
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."

# Build and serve documentation locally
serve: html
	@echo "Starting local server at http://localhost:8080"
	@cd $(BUILDDIR)/html && python -m http.server 8080

# Clean build directory
clean:
	rm -rf $(BUILDDIR)/*

# Build documentation with auto-reload for development
livehtml:
	sphinx-autobuild -b html --host 0.0.0.0 --port 8080 --watch ../app $(SOURCEDIR) $(BUILDDIR)/html

# Check for broken links
linkcheck:
	@$(SPHINXBUILD) -b linkcheck "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Generate API documentation stubs
apidoc:
	sphinx-apidoc -o . ../app --separate --force --no-toc

# Build all formats
all: clean html

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
