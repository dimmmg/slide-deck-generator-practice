install:
	npm ci
test:
	python -m unittest discover -s tests -v
demo:
	python generate_slides.py --plan examples/lesson.md --output out --pdf
run-cli:
	python generate_slides.py --plan $(PLAN) --output $(OUTPUT)
