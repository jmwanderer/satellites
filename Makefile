.PHONY: test

test:
	python3 -m unittest tests.py
	PYTHONPATH=. python3 -m unittest mnet/tests.py


large_test: test
	python3 -m unittest large_tests.py

