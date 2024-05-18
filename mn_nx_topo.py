import os
import shutil

import networkx
import mininet.topo
import mininet.node
import mininet.net

import forty_forty_topo
import topo_annotate

# TODO:
# Change linux router to FrrRouter
# Pick a better name for this module (and others)
# Fix assignment of main IP for first eth0 - want on lo I think.
#  mininet doesn't make this easy???

class LinuxRouter(mininet.node.Node):
    CFG_DIR="/etc/frr/{node}"
    LOG_DIR="/var/log/frr/{node}"

    def config(self, **params):
        # Get frr config and save to frr config directory
        cfg_dir = LinuxRouter.CFG_DIR.format(node=self.name)
        print(f"create {cfg_dir}")
        print(self.cmd(f"sudo install -m 775 -o frr -g frrvty -d {cfg_dir}"))

        log_dir = LinuxRouter.LOG_DIR.format(node=self.name)
        print(f"create {log_dir}")
        print(self.cmd(f"sudo install -m 775 -o frr -g frr -d  {log_dir}"))

        self.write_cfg_file(f"{cfg_dir}/vtysh.conf", params["vtysh"])
        self.write_cfg_file(f"{cfg_dir}/daemons", params["daemons"])
        self.write_cfg_file(f"{cfg_dir}/frr.conf", params["ospf"])

        super(LinuxRouter, self).config(**params)

    def write_cfg_file(self, file_path: str, contents: str) -> None:
        print(f"write {file_path}")
        with open(file_path, "w") as f:
            f.write(contents)
        os.chmod(file_path, 0o640)
        shutil.chown(file_path, "frr", "frr")


    def terminate(self):
        print("stop router")
        print(self.cmd(f"/usr/lib/frr/frrinit.sh stop '{self.name}'"))
        super(LinuxRouter, self).terminate()

    def start(self):
        # Start frr daemons
        print(f"start router {self.name}")
        print(self.cmd(f"/usr/lib/frr/frrinit.sh start '{self.name}'"))

    def stop(self, deleteIntfs=False):
        # Cleanup and stop frr daemons
        print(f"stop router {self.name}")
        super(LinuxRouter, self).stop(deleteIntfs)


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
        # TODO: double check base class - protected?
        # Create routers
        for name, node in self.graph.nodes.items():
            ip = node["ip"]
            self.addHost(name, cls=LinuxRouter, ip=format(ip),
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
    forty_forty_topo.create_network(graph, 8, 8)
    topo_annotate.annotate_graph(graph)
    topo = NetxTopo(graph)
    topo.build()

    for name, node in  graph.nodes.items():
        print(node['ospf'])
        print()



