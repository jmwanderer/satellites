.PHONY: test

test:
	python -m unittest tests.py
	PYTHONPATH=. python -m unittest mnet/tests.py


large_test: test
	python -m unittest large_tests.py

