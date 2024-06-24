#!/usr/bin/python3

"""
Run a mininet instance of FRR routers in a torus topology.
"""
import configparser
import signal
import sys

from mininet.net import Mininet
from mininet.log import setLogLevel, info
from mininet.cli import CLI
import mnet.driver

import torus_topo
import frr_config_topo
import mnet.frr_topo


def signal_handler(sig, frame):
    """
    Make a ^C start a clean shutdown. Needed to stop all of the FRR processes.
    """
    print("Ctrl-C recieved, shutting down....")
    mnet.driver.invoke_shutdown()

def run(num_rings, num_routers, use_cli, use_mnet, stable_monitors: bool, ground_stations: bool):
    # Create a networkx graph annoted with FRR configs
    graph = torus_topo.create_network(num_rings, num_routers, ground_stations)
    frr_config_topo.annotate_graph(graph)
    frr_config_topo.dump_graph(graph)

    # Use the networkx graph to build a mininet topology
    topo = mnet.frr_topo.NetxTopo(graph)
    print("generated topo")

    net = None
    if use_mnet:
        # Run mininet
        net = Mininet(topo=topo)
        net.start()

    frrt = mnet.frr_topo.FrrSimRuntime(topo, net, stable_monitors)
    print("created runtime")

    frrt.start_routers()

    print(f"\n****Running {num_rings} rings with {num_routers} per ring, stable monitors {stable_monitors}, ground_stations {ground_stations}")
    if use_cli and net is not None:
        CLI(net)
    else:
        print("Launching web API. Use /shutdown to halt")
        signal.signal(signal.SIGINT, signal_handler)
        mnet.driver.run(frrt)
    frrt.stop_routers()

    if net is not None:
        net.stop()


def usage():
    print("Usage: run_nm [--cli] [--no-mnet] <rings> <routers-per-ring>")
    print("<rings> - number of rings in the topology, 1 - 20")
    print("<routers-per-ring> - number of routers in each ring, 1 - 20")


if __name__ == "__main__":
    use_cli = False
    use_mnet = True
    if "--cli" in sys.argv:
        use_cli = True
        sys.argv.remove("--cli")

    if "--no-mnet" in sys.argv:
        use_mnet = False
        sys.argv.remove("--no-mnet")

    if len(sys.argv) > 2:
            usage()
            sys.exit(-1)

    parser = configparser.ConfigParser()
    parser['network'] = {}
    parser['monitor'] = {}
    try:
        if len(sys.argv) == 2:
            parser.read(sys.argv[1])
    except Exception as e:
        print(str(e))
        usage()
        sys.exit(-1)

    num_rings = parser['network'].getint('rings', 4)
    num_routers = parser['network'].getint('routers', 4)
    ground_stations = parser['network'].getboolean('ground_stations', False)
    stable_monitors = parser['monitor'].getboolean('stable_monitors', False)

    if num_rings < 1 or num_rings > 30 or num_routers < 1 or num_routers > 30:
        print("Rings or nodes count out of range")
        sys.exit(-1)

    setLogLevel("info")
    run(num_rings, num_routers, use_cli, use_mnet, stable_monitors, ground_stations)
