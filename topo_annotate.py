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
        count += 2
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
        graph.adj[n1][n2]['ip'][n1] = ipaddress.IPv4Interface((ips[0].packed, 30))
        graph.adj[n2][n1]['ip'][n2] = ipaddress.IPv4Interface((ips[1].packed, 30))

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

    for name, node in graph.nodes.items():
        node['ospf'] = create_ospf_config(graph, name)
        node['vtysh'] = create_vtysh_config(name)
        node['daemons'] = create_daemons_config()


OSPF_TEMPLATE = """
hostname {name}
frr defaults datacenter
log syslog informational
ip forwarding
no ipv6 forwarding
service integrated-vtysh-config
!
router ospf
 ospf router-id {ip}
{networks}
exit
!
"""

OSPF_NW_TEMPLATE = """ network {network} area 0.0.0.0"""

def create_ospf_config(graph: networkx.Graph, name: str) -> str:
    node = graph.nodes[name]
    ip = node["ip"]
    networks = []
    for neighbor in graph.adj[name]:
        edge = graph.adj[name][neighbor]
        networks.append(edge["ip"][name])

    networks_str = []
    network = ipaddress.IPv4Network((ip, 32))
    networks_str.append(OSPF_NW_TEMPLATE.format(network=format(network)))

    for network in networks:
        networks_str.append(OSPF_NW_TEMPLATE.format(network=format(network)))

    return OSPF_TEMPLATE.format(name=name,
                                ip=format(ip),
                                networks='\n'.join(networks_str))

def create_daemons_config() -> str:
    return """#
ospfd=yes
vtysh_enable=yes
zebra_options="  -A 127.0.0.1 -s 90000000"
mgmtd_options="  -A 127.0.0.1"
ospfd_options="  -A 127.0.0.1"
    """

def create_vtysh_config(name: str) -> str:
    return """service integrated-vtysh-config
hostname {name}""".format(name=name)


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


