import os
import grp
import pwd
import ipaddress
import tempfile
import shutil

import networkx
import mininet.topo
import mininet.node
import mininet.net
import mininet.link
import mininet.util

import torus_topo
import frr_config_topo
import mnet.pmonitor


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

        # Optional loopback interface
        self.loopIntf = None
        fd, self.working_db = tempfile.mkstemp(suffix=".sqlite")
        open(fd, "r").close()
        print(f"{self.name} db file {self.working_db}")

    def defaultIntf(self):
        # If we have a loopback, that is the default interface.
        # Otherwise use mininet default behavior.
        if self.loopIntf is not None:
            return self.loopIntf
        return super().defaultIntf()

    def config(self, **params):
        # Get frr config and save to frr config directory
        cfg_dir = FrrRouter.CFG_DIR.format(node=self.name)
        log_dir = FrrRouter.LOG_DIR.format(node=self.name)
        uinfo = pwd.getpwnam('frr')

        if not os.path.exists(cfg_dir):
            # sudo install -m 775 -o frr -g frrvty -d {cfg_dir}
            print(f"create {cfg_dir}")
            os.makedirs(cfg_dir, mode = 0o775)
            gid = grp.getgrnam('frrvty').gr_gid
            os.chown(cfg_dir, uinfo.pw_uid, gid)

        # sudo install -m 775 -o frr -g frr -d  {log_dir}
        if not os.path.exists(log_dir):
            print(f"create {log_dir}")
            os.makedirs(log_dir, mode = 0o775)
            os.chown(log_dir, uinfo.pw_uid, uinfo.pw_gid)

        self.write_cfg_file(f"{cfg_dir}/vtysh.conf", params["vtysh"], 
                            uinfo.pw_uid, uinfo.pw_gid)
        self.write_cfg_file(f"{cfg_dir}/daemons", params["daemons"], 
                            uinfo.pw_uid, uinfo.pw_gid)
        self.write_cfg_file(f"{cfg_dir}/frr.conf", params["ospf"], 
                            uinfo.pw_uid, uinfo.pw_gid)

        # If we have a default IP and it is not an existing interface, create a 
        # loopback.
        if params.get('ip') is not None:
            match_found = False
            ip = format(ipaddress.IPv4Interface(params.get('ip')).ip)
            for intf in self.intfs.values():
                if intf.ip == ip:
                    match_found = True
            if not match_found:
                # Make a default interface
                mininet.util.quietRun('ip link add name loop type dummy')
                self.loopIntf = mininet.link.Intf(name='loop', node=self)

        super().config(**params)

    def setIP(self, ip):
        mininet.node.Node.setIP(self, ip)

    def write_cfg_file(self, file_path: str, 
                       contents: str, uid: int, gid: int) -> None:
        print(f"write {file_path}")
        with open(file_path, "w") as f:
            f.write(contents)
            f.close()
        os.chmod(file_path, 0o640)
        os.chown(file_path, uid, gid)

    def startRouter(self):
        # Start frr daemons
        print(f"start router {self.name}")
        self.sendCmd(f"/usr/lib/frr/frrinit.sh start '{self.name}'")


    def startMonitor(self, db_master_file):
        self.sendCmd(f"python3 -m mnet.pmonitor monitor '{db_master_file}' '{self.working_db}' {self.defaultIntf().ip} &")


    def stopRouter(self, db_master):
        # Cleanup and stop frr daemons
        print(f"stop router {self.name}")
        mnet.pmonitor.set_can_run(db_master, self.defaultIntf().ip, False)
        self.sendCmd(f"/usr/lib/frr/frrinit.sh stop '{self.name}'")
        os.unlink(self.working_db)


class NetxTopo(mininet.topo.Topo):
    def __init__(self, graph: networkx.Graph):
        self.graph = graph
        self.routers: list[str] = []
        fd, self.db_file = tempfile.mkstemp(suffix=".sqlite")
        open(fd, "r").close()
        print(f"Master db file {self.db_file}")
        super(NetxTopo, self).__init__()

    def start_routers(self, net: mininet.net.Mininet):
        # Populate master db file
        data = []
        for name in self.routers:
            router = net.getNodeByName(name)
            data.append((router.name, router.defaultIntf().ip))
        mnet.pmonitor.init_targets(self.db_file, data)

        # Start routing
        for name in self.routers:
            router = net.getNodeByName(name)
            router.startRouter()
        # Wait for start to complete.
        for name in self.routers:
            router = net.getNodeByName(name)
            router.waitOutput()

        # Start monitoring
        for name in self.routers:
            router = net.getNodeByName(name)
            router.startMonitor(self.db_file)
        # Wait for start to complete.
        for name in self.routers:
            router = net.getNodeByName(name)
            router.waitOutput()

    def stop_routers(self, net: mininet.net.Mininet):
        db_master = mnet.pmonitor.open_db(self.db_file)
        for name in self.routers:
            router = net.getNodeByName(name)
            router.stopRouter(db_master)
        db_master.close()

        # Wait for start to complete - important!.
        # Otherwise processes may not shut down.
        for name in self.routers:
            router = net.getNodeByName(name)
            router.waitOutput()
        os.unlink(self.db_file)

    def build(self, **_opts):
        # Create routers
        for name, node in self.graph.nodes.items():
            ip = node.get("ip")
            if ip is not None:
                ip = format(ip)

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



