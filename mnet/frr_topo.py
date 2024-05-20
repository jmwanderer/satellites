import os
import shutil

import networkx
import mininet.topo
import mininet.node
import mininet.net
import mininet.link
import mininet.util

import torus_topo
import frr_config_topo


class FrrRouter(mininet.node.Node):
    """
    Support an FRR router under mininet.
    - handles the the FRR config files, starting and stopping FRR.

    Includes an optional loopback interface with a /31 subnet mask
    Does not cleanup config files.
    """

    CFG_DIR="/etc/frr/{node}"
    LOG_DIR="/var/log/frr/{node}"

    def __init__(self, name, **params):
        mininet.node.Node.__init__(self, name, **params)

        # Handle an optional loopback interface
        self.loopIntf = None

        if params.get('ip') is not None:
            # Make a default interface
           mininet.util.quietRun('ip link add name loop type dummy')
           self.loopIntf = mininet.link.Intf(name='loop', node=self)

    def defaultIntf(self):
        if self.loopIntf is not None:
            return self.loopIntf
        return super().defaultIntf()

    def config(self, **params):
        # Get frr config and save to frr config directory
        cfg_dir = FrrRouter.CFG_DIR.format(node=self.name)
        print(f"create {cfg_dir}")
        print(self.cmd(f"sudo install -m 775 -o frr -g frrvty -d {cfg_dir}"))

        log_dir = FrrRouter.LOG_DIR.format(node=self.name)
        print(f"create {log_dir}")
        print(self.cmd(f"sudo install -m 775 -o frr -g frr -d  {log_dir}"))

        self.write_cfg_file(f"{cfg_dir}/vtysh.conf", params["vtysh"])
        self.write_cfg_file(f"{cfg_dir}/daemons", params["daemons"])
        self.write_cfg_file(f"{cfg_dir}/frr.conf", params["ospf"])

        super().config(**params)

    def setIP(self, ip):
        # Make the default interface have a /31 mask
        mininet.node.Node.setIP(self, ip, prefixLen=31)

    def write_cfg_file(self, file_path: str, contents: str) -> None:
        print(f"write {file_path}")
        with open(file_path, "w") as f:
            f.write(contents)
        os.chmod(file_path, 0o640)
        shutil.chown(file_path, "frr", "frr")

    def terminate(self):
        print(f"stop router {self.name}")
        self.cmd(f"/usr/lib/frr/frrinit.sh stop '{self.name}'")
        super().terminate()

    def start(self):
        # Start frr daemons
        print(f"start router {self.name}")
        output = self.cmd(f"/usr/lib/frr/frrinit.sh start '{self.name}'")
        print(output)

    def stop(self, deleteIntfs=False):
        # Do we need this? or just terminate?
        # Cleanup and stop frr daemons
        print(f"stop router {self.name}")
        super().stop(deleteIntfs)


class NetxTopo(mininet.topo.Topo):
    def __init__(self, graph: networkx.Graph):
        self.graph = graph
        self.routers: list[str] = []
        super(NetxTopo, self).__init__()

    def start_routers(self, net: mininet.net.Mininet):
        for name in self.routers:
            router = net.getNodeByName(name)
            router.start()

    def build(self, **_opts):
        # Create routers
        for name, node in self.graph.nodes.items():
            ip = node.get("ip")
            if ip is not None:
                ip=format(ip)

            self.addHost(name, cls=FrrRouter, 
                         ip=ip,
                         ospf=node["ospf"],
                         vtysh=node["vtysh"],
                         daemons=node["daemons"])
            self.routers.append(name)

        # Create links between routers
        for name, edge in self.graph.edges.items():
            router1 = name[0]
            ip1 = edge["ip"][router1]
            intf1 = edge["intf"][router1]

            router2 = name[1]
            ip2 = edge["ip"][router2]
            intf2 = edge["intf"][router2]

            self.addLink(router1,
                         router2,
                         intfName1=intf1,
                         intfName2=intf2,
                         params1={'ip': format(ip1) },
                         params2={'ip': format(ip2) })



if __name__ == "__main__":
    graph = networkx.Graph()
    torus_topo.create_network(graph, 8, 8)
    frr_config_topo.annotate_graph(graph)
    topo = NetxTopo(graph)
    topo.build()

    for name, node in  graph.nodes.items():
        print(node['ospf'])
        print()



