#!/usr/bin/python3

"""
Run a mininet instance of FRR routers in a torus topology.
"""

from mininet.net import Mininet
from mininet.log import setLogLevel, info
from mininet.cli import CLI

# TODO:
# - Run frr deamons
# - Create configs for frr daemons

import networkx
import torus_topo
import frr_config_topo
import mnet.frr_topo

def run():
    # Create a networkx graph annoted with FRR configs
    graph = networkx.Graph()
    torus_topo.create_network(graph, 2, 2)
    frr_config_topo.annotate_graph(graph)
    frr_config_topo.dump_graph(graph)

    # Use the networkx graph to build a mininet topology
    topo = mnet.frr_topo.NetxTopo(graph)

    # Run mininet
    net = Mininet(topo=topo)
    net.start()
    topo.start_routers(net)
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()


