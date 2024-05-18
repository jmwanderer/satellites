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






if __name__ == "__main__":
    graph = networkx.Graph()
    forty_forty_topo.create_network(graph, 8, 8)
    topo_annotate.annotate_graph(graph)
    topo = NetxTopo(graph)
    topo.build()







