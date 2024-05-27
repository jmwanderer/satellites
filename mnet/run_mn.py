#!/usr/bin/python3

"""
Run a mininet instance of FRR routers in a torus topology.
"""
import signal
import sys

from mininet.net import Mininet
from mininet.log import setLogLevel, info
from mininet.cli import CLI
import mnet.driver

# TODO:
# - Run frr deamons
# - Create configs for frr daemons

import networkx
import torus_topo
import frr_config_topo
import mnet.frr_topo

def signal_handler(sig, frame):
    print("Ctrl-C recieved, shutting down....")
    mnet.driver.invoke_shutdown()

def run(num_rings, num_routers, use_cli):
    # Create a networkx graph annoted with FRR configs
    graph = networkx.Graph()
    torus_topo.create_network(graph, num_rings, num_routers)
    frr_config_topo.annotate_graph(graph)
    frr_config_topo.dump_graph(graph)

    # Use the networkx graph to build a mininet topology
    topo = mnet.frr_topo.NetxTopo(graph)

    # Run mininet
    net = Mininet(topo=topo)
    net.start()
    topo.start_routers(net)
    if use_cli:
        CLI(net)
    else:
        print("Launching web API. Use /shutdown to halt")
        signal.signal(signal.SIGINT, signal_handler)
        driver = mnet.driver.run(topo, net)
    topo.stop_routers(net)
    net.stop()


def usage():
    print("Usage: run_nm <rings> <routers-per-ring>")
    print("<rings> - number of rings in the topology, 1 - 20")
    print("<routers-per-ring> - number of routers in each ring, 1 - 20")


if __name__ == '__main__':
    use_cli = False
    if "--cli" in sys.argv:
        use_cli = True
        sys.argv.remove("--cli")

    if len(sys.argv) != 1 and len(sys.argv) != 3:
        usage()
        sys.exit(-1)


    num_rings = 4
    num_routers = 4

    if len(sys.argv) > 1:
        try:
            num_rings = int(sys.argv[1])   
            num_routers = int(sys.argv[2])   
        except:
            usage();
            sys.exit(-1)

    if num_rings < 1 or num_rings > 30 or num_routers < 1 or num_routers > 30:
        usage()
        sys.exit(-1)

    setLogLevel('info')
    print(f"Running {num_rings} rings with {num_routers} per ring")
    run(num_rings, num_routers, use_cli)


