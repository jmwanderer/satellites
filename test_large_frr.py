import torus_topo
import frr_config_topo
import networkx

"""
Simple text to configure a 40x40 satellite network
"""

graph = networkx.Graph()
torus_topo.create_network(graph)
frr_config_topo.annotate_graph(graph)
frr_config_topo.dump_graph(graph)


