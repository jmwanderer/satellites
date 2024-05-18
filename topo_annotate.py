import ipaddress

import networkx

def annotate_graph(graph: networkx.Graph):
    """
    Annotate a topology with IP address for each node and IP address and interface names for each edge.
    """
    count = 1
    for node in graph.nodes.values():
        # Configure node with an ip address
        node['inf_count'] = 0
        node['number'] = count
        ip = 0x0a010000 + count
        count += 1
        node['ip'] = ipaddress.IPv4Address(ip)

    count = 1
    for edge in graph.edges.values():
        # Configure edge with a subnet
        edge['number'] = count
        ip = 0x0a0f0000 + count * 4
        count += 1
        edge['ip'] = ipaddress.IPv4Network((ip, 30))

    for n1, n2 in graph.edges:
        # Set ip addresses for each end of an edge
        edge = graph.edges[n1, n2]
        ips = list(edge['ip'].hosts())
        graph.adj[n1][n2]['ip'] = {}
        graph.adj[n1][n2]['ip'][n1] = ips[0]
        graph.adj[n2][n1]['ip'][n2] = ips[1]

        # Set interface names for each end of an edge
        c = graph.nodes[n1]['inf_count'] + 1
        graph.nodes[n1]['inf_count'] = c
        intf1 = f'{n1}-eth{c}'

        c = graph.nodes[n2]['inf_count'] + 1
        graph.nodes[n2]['inf_count'] = c
        intf2 = f'{n2}-eth{c}'

        graph.adj[n1][n2]['intf'] = {}
        graph.adj[n1][n2]['intf'][n1] = intf1
        graph.adj[n2][n1]['intf'][n2] = intf2


def dump_graph(graph: networkx.Graph):
    for name, node in graph.nodes.items():
        print(f'node: {name} - {format(node["ip"])}')
        for neighbor in graph.adj[name]:
            edge = graph.adj[name][neighbor]
            print(f'\t{format(edge["ip"][name])}  : {edge["intf"][name]} to {neighbor} ({format(edge["ip"][neighbor])})')

    print()
    for n, edge in graph.edges.items():
        print(f'edge: {n} - {format(edge["ip"])}')


def gen_test_graph() -> networkx.Graph:
    graph = networkx.Graph()

    graph.add_node('R1')
    graph.add_node('R2')
    graph.add_node('R3')
    graph.add_node('R4')

    graph.add_edge('R1', 'R2')
    graph.add_edge('R2', 'R3')
    graph.add_edge('R3', 'R4')
    graph.add_edge('R4', 'R1')
    return graph

if __name__ == "__main__":
    # Run a simple test
    g = gen_test_graph()
    annotate_graph(g)
    dump_graph(g)


