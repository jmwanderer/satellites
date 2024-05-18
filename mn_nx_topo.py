import networkx
import mininet.topo
import mininet.node

import forty_forty_topo
import topo_annotate

class LinuxRouter(mininet.node.Node):
    def config(self, **params):
        super(LinuxRouter, self).config(**params)

    def terminate(self):
        super(LinuxRouter, self).terminate()


class NetxTopo(mininet.topo.Topo):
    def __init__(self, graph: networkx.Graph):
        self.graph = graph
        super(NetxTopo, self).__init__()

    def build(self, **_opts):
        # Create routers
        routers = {}

        for name, node in self.graph.nodes.items():
            ip = node["ip"]
            router = self.addHost(name, cls=LinuxRouter, ip=format(ip))
            routers[name] = router

        # Create links between routers
        for name, edge in self.graph.edges.items():
            r1_name = name[0]
            router1 = routers[r1_name]
            ip1 = edge["ip"][r1_name]
            intf1 = edge["intf"][r1_name]

            r2_name = name[1]
            router2 = routers[r2_name]
            ip2 = edge["ip"][r2_name]
            intf2 = edge["intf"][r2_name]

            self.addLink(router1,
                         router2,
                         intfName1=intf1,
                         intfName2=intf2,
                         params1={'ip': format(ip1) },
                         params2={'ip': format(ip2) })



OSPF_TEMPLATE = """
hostname {name}
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
    for network in networks:
        networks_str.append(OSPF_NW_TEMPLATE.format(network=format(network)))

    return OSPF_TEMPLATE.format(name=name,
                                ip=format(ip),
                                networks='\n'.join(networks_str))



if __name__ == "__main__":
    graph = networkx.Graph()
    forty_forty_topo.create_network(graph, 8, 8)
    topo_annotate.annotate_graph(graph)
    topo = NetxTopo(graph)
    topo.build()

    for name, node in  graph.nodes.items():
        config = create_ospf_config(graph, name)
        print(config)
        print()



