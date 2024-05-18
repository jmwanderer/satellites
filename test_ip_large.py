import forty_forty_topo
import topo_annotate
import networkx

"""
Simple text to configure a 40x40 satellite network
"""

graph = networkx.Graph()
forty_forty_topo.create_network(graph)
topo_annotate.annotate_graph(graph)
topo_annotate.dump_graph(graph)


