.PHONY: test

test:
	python torus_topo.py
	python frr_config_topo.py
	python test_large_frr.py
	python sat_pos_samples.py
