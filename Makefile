LAYOUTS=page.html

all: pages

pages: $(shell find templates -name \*.html $(addprefix \! -name ,$(LAYOUTS)) -printf %P\\n)

%.html: templates/%.html
	mkdir -p $(shell dirname $@)
	python build.py page <$< >$@

.PHONY: all pages
