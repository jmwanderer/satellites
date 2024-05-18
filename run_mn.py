#!/usr/bin/python3
from mininet.net import Mininet
from mininet.log import setLogLevel, info
from mininet.cli import CLI

import networkx
import mn_nx_topo
import forty_forty_topo
import topo_annotate

def run():
    graph = networkx.Graph()
    forty_forty_topo.create_network(graph, 8, 8)
    topo_annotate.annotate_graph(graph)
    topo_annotate.dump_graph(graph)
    topo = mn_nx_topo.NetxTopo(graph)

    net = Mininet(topo=topo)

    net.start()
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()


