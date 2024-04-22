"""
Create a LEO satellite network topology.
"""

import networkx

num_rings = 40
num_ring_nodes = 40

def get_node_name(ring_num, node_num):
    return f"{ring_num}:{node_num}"

def create_ring(graph, ring_num):
    prev_node = None
    for node_num in range(num_ring_nodes):
        # Create a node in the ring
        node_name = get_node_name(ring_num, node_num)
        graph.add_node(node_name)

        # Create a link to the previously created node
        if prev_node is not None:
            graph.add_edge(prev_node, node_name)
        prev_node = node_name
    # Create a link between first and last node
    if prev_node is not None:
        graph.add_edge(prev_node, get_node_name(ring_num, 0))

def connect_rings(graph, ring1, ring2):
    for node_num in range(num_ring_nodes):
        node1 = get_node_name(ring1, node_num)
        node2 = get_node_name(ring2, node_num)
        graph.add_edge(node1, node2)

def create_network(graph):
    prev_ring_num = None
    for ring_num in range(num_rings):
        create_ring(graph, ring_num)
        if prev_ring_num is not None:
            connect_rings(graph, prev_ring_num, ring_num)
        prev_ring_num = ring_num
    if prev_ring_num is not None:
        connect_rings(graph, prev_ring_num, 0)
    
    # Set all edges to up
    for edge_name, edge in graph.edges.items():
        edge['up'] = True


graph = networkx.Graph()
create_network(graph)
    
print("Number nodes: %d" % graph.number_of_nodes())
print("Number edges: %d" % graph.number_of_edges())
print(graph.nodes)
print(graph.edges)

def generate_route_table(graph, node_name):
    routes = {}  # Dest: (hops, [NH, ...])
    for name, node in graph.nodes.items():
        node['visited'] = False

    node_list = []
    graph.nodes[node_name]['visited'] = True

    def visit_node(graph, next_hop, path_len, node):
        if graph.nodes[node]['visited']:
            return
        graph.nodes[node]['visited'] = True

        routes[node] = (path_len, [next_hop])

        for neighbor_node in graph.adj[node]:
            if graph.edges[node, neighbor_node]['up']:
                node_list.append((path_len + 1, next_hop, neighbor_node))

    for neighbor_node in graph.adj[node_name]:
        if graph.edges[node_name, neighbor_node]['up']:
            node_list.append((1, neighbor_node, neighbor_node))

    while len(node_list) > 0:
        path_len, next_hop, node = node_list.pop(0)
        visit_node(graph, next_hop, path_len, node)


    return routes

routes = generate_route_table(graph, get_node_name(0, 0))
for node, entry in routes.items():
    print("node: %s, next: %s, len: %d" % (node, entry[1][0], entry[0]))

route_tables = {}
for node_name in graph.nodes():
    print("generate routes %s" % node_name)
    route_tables[node_name] = generate_route_table(graph, node_name)

def trace_node(start_node, target_node):
    print("trace node %s to %s" % (start_node, target_node))
    current_node = start_node
    while current_node is not None and current_node != target_node:
        if route_tables[current_node].get(target_node) is None:
            current_node = None
            print("unreachable")
        else:
            entry = route_tables[current_node][target_node]
            next_hop = entry[1][0]
            print(next_hop)
            current_node = next_hop

trace_node(get_node_name(0,0), get_node_name(0,1))
print()
trace_node(get_node_name(0,0), get_node_name(0,2))
print()
trace_node(get_node_name(0,0), get_node_name(18,26))

