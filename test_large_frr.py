import torus_topo
import frr_config_topo

"""
Simple text to configure a 40x40 satellite network
"""

graph = torus_topo.create_network()
frr_config_topo.annotate_graph(graph)
frr_config_topo.dump_graph(graph)


