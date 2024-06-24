"""
Create a torus network topology.

This is a series of connected rings.
Include test code to generate route maps and test connectivity.
"""

from dataclasses import dataclass
from typing import ClassVar
import networkx
import datetime

# Default network size
NUM_RINGS = 40
NUM_RING_NODES = 40
TYPE = "type"
TYPE_SAT = "satellite"
TYPE_GROUND = "ground_station"
LAT = "latitude"
LON = "longitude"

def create_network(num_rings: int =NUM_RINGS, num_ring_nodes: int =NUM_RING_NODES, ground_stations: bool = True) -> networkx.Graph:
    """
    Create a torus network of the given size annotated with orbital information.
    """
    graph: networkx.Graph = networkx.Graph()
    graph.graph["rings"] = num_rings
    graph.graph["ring_nodes"] = num_ring_nodes
    graph.graph["ring_list"] = []
    graph.graph["inclination"] = 53.9
    prev_ring_num = None
    for ring_num in range(num_rings):
        create_ring(graph, ring_num, num_ring_nodes)
        if prev_ring_num is not None:
            connect_rings(graph, prev_ring_num, ring_num, num_ring_nodes)
        prev_ring_num = ring_num
    if prev_ring_num is not None:
        connect_rings(graph, prev_ring_num, 0, num_ring_nodes)

    if ground_stations:
        add_ground_stations(graph)

    # Set all edges to up
    for edge_name, edge in graph.edges.items():
        edge["up"] = True
    return graph

def ground_stations(graph: networkx.Graph) -> list[str]:
    """
    Return a list of all node names where the node is of type ground
    """
    # Consider converting to using yield
    result = []
    for name in graph.nodes:
        if graph.nodes[name][TYPE] == TYPE_GROUND:
            result.append(name)
    return result


def satellites(graph: networkx.Graph) -> list[str]:
    """
    Return a list of all node names where the node is of type satellite
    """
    # Consider converting to using yield
    result = []
    for name in graph.nodes:
        if graph.nodes[name][TYPE] == TYPE_SAT:
            result.append(name)
    return result

# Format for generating TLE oribit information
# Use canned IU, mean motion derivitivs, and drag term data
LINE1 = "1 {:05d}U 24067A   {:2d}{:012.8f}  .00009878  00000-0  47637-3 0  999"
# Use a perigee of 297 (could just be 0). Canned data for orbit count, prbits per day,
# and exccentricity
LINE2 = "2 {:05d} {:8.4f} {:8.4f} 0003572 297.6243 {:8.4f} 15.33600000 6847"


@dataclass
class OrbitData:
    """Records key orbital information"""

    right_ascension: float  # degrees
    inclination: float  # degrees
    mean_anomaly: float  # degrees
    cat_num: int = 0

    cat_num_count: ClassVar[int] = 1

    def assign_cat_num(self) -> None:
        self.cat_num = OrbitData.cat_num_count
        OrbitData.cat_num_count += 1

    @staticmethod
    def tle_check_sum(line: str) -> str:
        val = 0
        for i in range(len(line)):
            if line[i] == "-":
                val += 1
            elif line[i].isdigit():
                val += int(line[i])
        return str(val % 10)

    def tle_format(self) -> tuple[str,str]:
        time_tuple = datetime.datetime.now().timetuple()
        year = time_tuple.tm_year % 1000 % 100
        day = time_tuple.tm_yday
        
        l1 = LINE1.format(self.cat_num, year, day, 342)
        l2 = LINE2.format(
            self.cat_num, self.inclination, self.right_ascension, self.mean_anomaly
        )
        l1 = l1 + OrbitData.tle_check_sum(l1)
        l2 = l2 + OrbitData.tle_check_sum(l2)
        return l1, l2


def get_node_name(ring_num: int, node_num: int) -> str:
    return f"R{ring_num}_{node_num}"


def create_ring(graph: networkx.Graph, ring_num: int , num_ring_nodes: int) -> None:
    prev_node_name: str|None = None
    ring_nodes: list[str] = []
    graph.graph["ring_list"].append(ring_nodes)

    # Set parameters for this orbit
    num_rings: int = graph.graph["rings"]
    right_ascension: float = 360 / num_rings * ring_num
    inclination: float = graph.graph["inclination"]

    for node_num in range(num_ring_nodes):
        # Create a node in the ring
        node_name = get_node_name(ring_num, node_num)
        graph.add_node(node_name)
        graph.nodes[node_name][TYPE] = TYPE_SAT
        mean_anomaly = 360 / num_ring_nodes * node_num
        # offset 1/2 spacing for odd rings
        if ring_num % 2 == 1:
            mean_anomaly += 360 / num_ring_nodes / 2
        orbit = OrbitData(right_ascension, inclination, mean_anomaly)
        orbit.assign_cat_num()
        graph.nodes[node_name]["orbit"] = orbit
        ring_nodes.append(node_name)

        # Create a link to the previously created node
        if prev_node_name is not None:
            graph.add_edge(prev_node_name, node_name)
            graph.edges[prev_node_name, node_name]["inter_ring"] = False
        prev_node_name = node_name
    # Create a link between first and last node
    if prev_node_name is not None:
        graph.add_edge(prev_node_name, get_node_name(ring_num, 0))
        graph.edges[prev_node_name, get_node_name(ring_num, 0)]["inter_ring"] = False


def connect_rings(graph: networkx.Graph, ring1: int, ring2: int, num_ring_nodes: int) -> None:
    for node_num in range(num_ring_nodes):
        node1_name = get_node_name(ring1, node_num)
        node2_name = get_node_name(ring2, node_num)
        graph.add_edge(node1_name, node2_name)
        graph.edges[node1_name, node2_name]["inter_ring"] = True


def add_ground_stations(graph: networkx.Graph) -> None:
    # Create ground stations with links
    # We need links because mininet doesn't handle nodes without links the
    # way we want (e.g. will not call config on the mininet node)
    graph.add_node("G_PAO")
    node = graph.nodes["G_PAO"]
    node[TYPE] = TYPE_GROUND
    node[LAT] = 37.44651
    node[LON] = -122.13861

    graph.add_node("G_SYD")
    node = graph.nodes["G_SYD"]
    node[TYPE] = TYPE_GROUND
    node[LAT] = -33.94056
    node[LON] = 151.17268
    graph.add_edge("G_PAO", "G_SYD")

    graph.add_node("G_ZRH")
    node = graph.nodes["G_ZRH"]
    node[TYPE] = TYPE_GROUND
    node[LAT] = 47.45516
    node[LON] = 8.56350
    graph.add_edge("G_SYD", "G_ZRH")

    graph.add_node("G_HND")
    node = graph.nodes["G_HND"]
    node[TYPE] = TYPE_GROUND
    node[LAT] = 35.54852
    node[LON] = 139.78079
    graph.add_edge("G_ZRH", "G_HND")
    graph.add_edge("G_HND", "G_PAO")


#
# Functions to exercise basic routing over the torus topology graph 
#

def down_inter_ring_links(graph: networkx.Graph, node_num_list: list[int], num_rings=NUM_RINGS):
    """
    Mark the inter-ring links down for the specified node numbers on all rings 
    to prevent use during a path trace. This causes many inter-ring links to be down to 
    test the routing functions.
    """
    # Set the specified links to down
    for node_num in node_num_list:
        for ring_num in range(num_rings):
            node_name = get_node_name(ring_num, node_num)
            for neighbor_name in graph.adj[node_name]:
                if graph[node_name][neighbor_name]["inter_ring"]:
                    graph[node_name][neighbor_name]["up"] = False


def generate_route_table(graph: networkx.Graph, node_name: str) -> dict[str,tuple[int,str]]:
    """
    Breadth first search to generate routes fromthe  start node to all other nodes.
    Routing table provides a next hop and a path length for all possible destinations.

    { "dest node" : ( path_len, "next hop" )}
    """

    routes = {}  # Dest: (hops, next hop node)
    for name, node in graph.nodes.items():
        node["visited"] = False

    # Queue to nodes to visit
    node_list = []
    # Mark the start node as visited
    graph.nodes[node_name]["visited"] = True

    def visit_node(graph: networkx.Graph, next_hop: str, path_len: int, visit_node_name: str) -> None:
        """
        Visit a node by adding all neighbors to the visit queue
        """
        # Neighbors already visted are added to the queue, we skip them here
        if graph.nodes[visit_node_name]["visited"]:
            return
        graph.nodes[visit_node_name]["visited"] = True

        # This node is reachable from the start node via the given 
        # next hop from the start node
        routes[visit_node_name] = (path_len, next_hop)

        # Enqueue is reachable neighbor for a future visit
        for neighbor_node_name in graph.adj[visit_node_name]:
            if graph.edges[visit_node_name, neighbor_node_name]["up"]:
                node_list.append((path_len + 1, next_hop, neighbor_node_name))

    # Enqueue the neighbors of the start node for visiting
    for neighbor_node_name in graph.adj[node_name]:
        if graph.edges[node_name, neighbor_node_name]["up"]:
            node_list.append((1, neighbor_node_name, neighbor_node_name))

    # Visit all nodes until the queue is empty
    while len(node_list) > 0:
        path_len, next_hop, visit_node_name = node_list.pop(0)
        visit_node(graph, next_hop, path_len, visit_node_name)

    return routes


def trace_path(start_node_name: str, target_node_name: str, route_tables: dict[str,dict[str,tuple[int,str]]]) -> bool:
    """
    Follow the routing tables to trace a path between the start and target node
    route_tables is a dictionary of routes for each source node
    """
    unreachable_count: int = 0
    print("trace node %s to %s" % (start_node_name, target_node_name))
    current_node_name: str | None = start_node_name

    # Follow path until we reach the target or it is unreachable
    while current_node_name is not None and current_node_name != target_node_name:
        if route_tables[current_node_name].get(target_node_name) is None:
            current_node_name = None
            print("unreachable")
        else:
            entry = route_tables[current_node_name][target_node_name]
            next_hop_name = entry[1]
            print(next_hop_name)
            current_node_name = next_hop_name
    return current_node_name is not None


def run_small_test() -> bool:
    """
    Make a graph
    """
    graph: networkx.Graph = create_network()
    return True

def run_routing_test() -> bool:
    """
    Make a graph and exercise path tracing
    """
    graph: networkx.Graph = create_network()

    down_inter_ring_links(graph, [0, 1, 2, 3, 4, 5, 20, 21, 22, 23, 24, 25])

    print("Number nodes: %d" % graph.number_of_nodes())
    print("Number edges: %d" % graph.number_of_edges())
    print(graph.nodes)
    print(graph.edges)

    for node in satellites(graph):
        print(node)
        orbit = graph.nodes[node]["orbit"]
        print(orbit)
        l1, l2 = orbit.tle_format()
        print(l1)
        print(l2)
        print()

    routes = generate_route_table(graph, get_node_name(0, 0))
    for node, entry in routes.items():
        print("node: %s, next: %s, len: %d" % (node, entry[1][0], entry[0]))

    route_tables = {}
    for node_name in graph.nodes():
        print("generate routes %s" % node_name)
        route_tables[node_name] = generate_route_table(graph, node_name)
        print(f"len: {len(route_tables[node_name])}")

    result: bool = trace_path(get_node_name(0, 0), get_node_name(0, 1), route_tables)
    print()
    result = result and trace_path(get_node_name(0, 0), get_node_name(0, 2), route_tables)
    print()
    result = result and trace_path(get_node_name(0, 0), get_node_name(1, 0), route_tables)
    print()
    result = result and trace_path(get_node_name(0, 0), get_node_name(18, 26), route_tables)
    return result


if __name__ == "__main__":
    run_routing_test()
