#!/usr/bin/python3
from mininet.net import Mininet
from mininet.log import setLogLevel, info
from mininet.cli import CLI

# TODO:
# - Run frr deamons
# - Create configs for frr daemons

import networkx
import mn_nx_topo
import torus_topo
import frr_config_topo


def run():
    graph = networkx.Graph()
    torus_topo.create_network(graph, 2, 2)
    frr_config_topo.annotate_graph(graph)
    frr_config_topo.dump_graph(graph)
    topo = mn_nx_topo.NetxTopo(graph)

    net = Mininet(topo=topo)
    net.start()
    topo.start_routers(net)
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()


