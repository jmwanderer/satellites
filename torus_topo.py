"""
Create a torus network topology.

This is a series of connected rings.
Include test code to generate route maps and test connectivity.
"""

from dataclasses import dataclass
from typing import ClassVar
import networkx

NUM_RINGS = 40
NUM_RING_NODES = 40


# Use canned IU, mean motion derivitivs, and drag term data
LINE1 = '1 {:05d}U 24067A   {:2d}{:012.8f}  .00009878  00000-0  47637-3 0  999'
# Use a perigee of 297 (could just be 0). Canned data for orbit count, prbits per day,
# and exccentricity
LINE2 = '2 {:05d} {:8.4f} {:8.4f} 0003572 297.6243 {:8.4f} 15.33600000 6847'

@dataclass 
class OrbitData:
    """Records key orbital information"""
    right_ascension: float      # degrees
    inclination: float          # degrees
    mean_anomaly: float         # degrees
    cat_num: int = 0           

    cat_num_count: ClassVar[int] = 1

    def assign_cat_num(self) -> None:
        self.cat_num = OrbitData.cat_num_count
        OrbitData.cat_num_count += 1

    def tle_check_sum(line: str) -> str:
        val = 0
        for i in range(len(line)):
            if line[i] == '-':
                val += 1
            elif line[i].isdigit():
                val += int(line[i])
        return str(val % 10)

    def tle_format(self) -> tuple[str]:
        l1 = LINE1.format(self.cat_num, 23, 21, 342)
        l2 = LINE2.format(self.cat_num, self.inclination, self.right_ascension,
                          self.mean_anomaly)
        l1 = l1 + OrbitData.tle_check_sum(l1)
        l2 = l2 + OrbitData.tle_check_sum(l2)
        return l1, l2

def get_node_name(ring_num, node_num):
    return f"R{ring_num}_{node_num}"

def create_ring(graph, ring_num, num_ring_nodes):
    prev_node_name = None
    ring_nodes = []
    graph.graph["ring_list"].append(ring_nodes)

    # Set parameters for this orbit
    num_rings: int = graph.graph["rings"]
    right_ascension: float = 360 / num_rings * ring_num
    inclination: float = graph.graph["inclination"]

    for node_num in range(num_ring_nodes):
        # Create a node in the ring
        node_name = get_node_name(ring_num, node_num)
        graph.add_node(node_name)
        mean_anomaly = 360 / num_ring_nodes * node_num
        # offset 1/2 spacing for odd rings
        if ring_num %2 == 1:
            mean_anomaly += 360 / num_ring_nodes / 2
        orbit = OrbitData(right_ascension, inclination, mean_anomaly)
        orbit.assign_cat_num()
        graph.nodes[node_name]['orbit'] = orbit
        ring_nodes.append(node_name)

        # Create a link to the previously created node
        if prev_node_name is not None:
            graph.add_edge(prev_node_name, node_name)
            graph.edges[prev_node_name, node_name]['inter_ring'] = False
        prev_node_name = node_name
    # Create a link between first and last node
    if prev_node_name is not None:
        graph.add_edge(prev_node_name, get_node_name(ring_num, 0))
        graph.edges[prev_node_name, get_node_name(ring_num,0 )]['inter_ring'] = False

def connect_rings(graph, ring1, ring2, num_ring_nodes):
    for node_num in range(num_ring_nodes):
        node1_name = get_node_name(ring1, node_num)
        node2_name = get_node_name(ring2, node_num)
        graph.add_edge(node1_name, node2_name)
        graph.edges[node1_name, node2_name]['inter_ring'] = True

def create_network(num_rings=NUM_RINGS, num_ring_nodes=NUM_RING_NODES):
    graph = networkx.Graph()
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
    
    # Set all edges to up
    for edge_name, edge in graph.edges.items():
        edge['up'] = True
    return graph

def down_inter_ring_links(graph, node_num_list, num_rings=NUM_RINGS):
    # Set the specified links to down
    for node_num in node_num_list:
        for ring_num in range(num_rings):
            node_name = get_node_name(ring_num, node_num)
            for neighbor_name in graph.adj[node_name]:
                if graph[node_name][neighbor_name]['inter_ring']:
                    graph[node_name][neighbor_name]['up'] = False

def generate_route_table(graph, node_name):
    routes = {}  # Dest: (hops, [NH, ...])
    for name, node in graph.nodes.items():
        node['visited'] = False

    node_list = []
    graph.nodes[node_name]['visited'] = True

    def visit_node(graph, next_hop, path_len, visit_node_name):
        if graph.nodes[visit_node_name]['visited']:
            return
        graph.nodes[visit_node_name]['visited'] = True

        routes[visit_node_name] = (path_len, [next_hop])

        for neighbor_node_name in graph.adj[visit_node_name]:
            if graph.edges[visit_node_name, neighbor_node_name]['up']:
                node_list.append((path_len + 1, next_hop, neighbor_node_name))

    for neighbor_node_name in graph.adj[node_name]:
        if graph.edges[node_name, neighbor_node_name]['up']:
            node_list.append((1, neighbor_node_name, neighbor_node_name))

    while len(node_list) > 0:
        path_len, next_hop, visit_node_name = node_list.pop(0)
        visit_node(graph, next_hop, path_len, visit_node_name)


    return routes

def trace_node(start_node_name, target_node_name):
    print("trace node %s to %s" % (start_node_name, target_node_name))
    current_node_name = start_node_name
    while current_node_name is not None and current_node_name != target_node_name:
        if route_tables[current_node_name].get(target_node_name) is None:
            current_node_name = None
            print("unreachable")
        else:
            entry = route_tables[current_node_name][target_node_name]
            next_hop_name = entry[1][0]
            print(next_hop_name)
            current_node_name = next_hop_name


if __name__ == "__main__":
    graph = create_network()

    down_inter_ring_links(graph, [0, 1, 2, 3, 4, 5, 20, 21, 22, 23, 24, 25])
    
    print("Number nodes: %d" % graph.number_of_nodes())
    print("Number edges: %d" % graph.number_of_edges())
    print(graph.nodes)
    print(graph.edges)

    for node in graph.nodes:
        print(node)
        orbit = graph.nodes[node]['orbit']
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


    trace_node(get_node_name(0,0), get_node_name(0,1))
    print()
    trace_node(get_node_name(0,0), get_node_name(0,2))
    print()
    trace_node(get_node_name(0,0), get_node_name(1,0))
    print()
    trace_node(get_node_name(0,0), get_node_name(18,26))


