import os
import grp
import pwd
import ipaddress
import tempfile
import datetime
import shutil
import random
import socket
import typing
from dataclasses import dataclass, field

import networkx
import mininet.topo
import mininet.node
import mininet.net
import mininet.link
import mininet.util

import torus_topo
import frr_config_topo
import simapi
import mnet.pmonitor


@dataclass
class IPPoolEntry:
    network: ipaddress.IPv4Network
    ip1: ipaddress.IPv4Interface
    ip2: ipaddress.IPv4Interface
    used: bool = False


@dataclass
class Uplink:
    sat_name: str
    distance: int
    ip_pool_entry: IPPoolEntry
    default: bool = False


class GroundStation:
    """
    State for a Ground Station

    Tracks established uplinks to satellites.
    Not a mininet node.
    """

    def __init__(self, name: str, uplinks: list[dict[str,typing.Any]]) -> None:
        self.name = name
        self.uplinks: list[Uplink] = []
        self.ip_pool: list[IPPoolEntry] = []
        for link in uplinks:
            entry = IPPoolEntry(network=link["nw"], ip1=link["ip1"], ip2=link["ip2"])
            self.ip_pool.append(entry)
            print(f"added pool entry {entry.network}")

    def has_uplink(self, sat_name: str) -> bool:
        for uplink in self.uplinks:
            if uplink.sat_name == sat_name:
                return True
        return False

    def sat_links(self) -> list[str]:
        """
        Return a list of satellite names to which we have uplinks
        """
        return [uplink.sat_name for uplink in self.uplinks]

    def _get_pool_entry(self) -> IPPoolEntry | None:
        for entry in self.ip_pool:
            if not entry.used:
                entry.used = True
                return entry
        return None

    def add_uplink(self, sat_name: str, distance: int) -> Uplink | None:
        pool_entry = self._get_pool_entry()
        if pool_entry is None:
            return None
        uplink = Uplink(sat_name, distance, pool_entry)
        self.uplinks.append(uplink)
        return uplink

    def remove_uplink(self, sat_name: str) -> Uplink|None:
        for entry in self.uplinks:
            if entry.sat_name == sat_name:
                entry.ip_pool_entry.used = False
                self.uplinks.remove(entry)
                return entry
        return None


class FrrRouterNode(mininet.node.Node):
    """
    Support an FRR router under mininet.
    This is a mininet node
    - handles the the FRR config files, starting and stopping FRR.

    Includes an optional loopback interface with a /31 subnet mask
    Does not cleanup config files.
    """

    CFG_DIR = "/etc/frr/{node}"
    VTY_DIR = "/var/frr/{node}/{daemon}.vty"
    LOG_DIR = "/var/log/frr/{node}"

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
        cfg_dir = FrrRouterNode.CFG_DIR.format(node=self.name)
        log_dir = FrrRouterNode.LOG_DIR.format(node=self.name)
        uinfo = pwd.getpwnam("frr")

        if not os.path.exists(cfg_dir):
            # sudo install -m 775 -o frr -g frrvty -d {cfg_dir}
            print(f"create {cfg_dir}")
            os.makedirs(cfg_dir, mode=0o775)
            gid = grp.getgrnam("frrvty").gr_gid
            os.chown(cfg_dir, uinfo.pw_uid, gid)

        # sudo install -m 775 -o frr -g frr -d  {log_dir}
        if not os.path.exists(log_dir):
            print(f"create {log_dir}")
            os.makedirs(log_dir, mode=0o775)
            os.chown(log_dir, uinfo.pw_uid, uinfo.pw_gid)

        self.write_cfg_file(
            f"{cfg_dir}/vtysh.conf", params["vtysh"], uinfo.pw_uid, uinfo.pw_gid
        )
        self.write_cfg_file(
            f"{cfg_dir}/daemons", params["daemons"], uinfo.pw_uid, uinfo.pw_gid
        )
        self.write_cfg_file(
            f"{cfg_dir}/frr.conf", params["ospf"], uinfo.pw_uid, uinfo.pw_gid
        )

        # If we have a default IP and it is not an existing interface, create a
        # loopback.
        if params.get("ip") is not None:
            match_found = False
            ip = format(ipaddress.IPv4Interface(params.get("ip")).ip)
            for intf in self.intfs.values():
                if intf.ip == ip:
                    match_found = True
            if not match_found:
                # Make a default interface
                mininet.util.quietRun("ip link add name loop type dummy")
                self.loopIntf = mininet.link.Intf(name="loop", node=self)

        super().config(**params)

    def frr_config_commands(self, commands: list[str]) -> bool:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        path = FrrRouterNode.VTY_DIR.format(node=self.name, daemon="ospfd")
        result = True
        try:
            sock.connect(path)
            msg = b'enable\x00'
            result = result and self._send_frr_cmd(sock, msg)
            msg = b'conf term file-lock\x00'
            result = result and self._send_frr_cmd(sock, msg)
            for command in commands:
                print(f"sending command {command} to {self.name}")
                msg = (command + '\x00').encode("ascii")
                result = result and self._send_frr_cmd(sock, msg)
            msg = b'end\x00'
            self._send_frr_cmd(sock, msg)
            msg = b'disable\x00'
            self._send_frr_cmd(sock, msg)
        except TimeoutError:
            print("timout connecting to FRR")
            result = False
        sock.close()
        return result

    def _send_frr_cmd(self, sock, msg: bytes) -> bool:
        sock.sendall(msg)
        data = sock.recv(10000)
        size = len(data)
        if size > 0 and data[size-1] == 0:
            return True
        return False


    def setIP(self, ip):
        mininet.node.Node.setIP(self, ip)

    def write_cfg_file(self, file_path: str, contents: str, uid: int, gid: int) -> None:
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

    def startMonitor(self, db_master_file, db_master):
        self.sendCmd(
            f"python3 -m mnet.pmonitor monitor '{db_master_file}' '{self.working_db}' {self.defaultIntf().ip} >> /dev/null 2>&1  &"
        )
        mnet.pmonitor.set_running(db_master, self.defaultIntf().ip, True)

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
        self.ground_stations: dict[str, GroundStation] = {}
        self.stat_samples = []
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
        db_master = mnet.pmonitor.open_db(self.db_file)
        for name in self.routers:
            router = net.getNodeByName(name)
            router.startMonitor(self.db_file, db_master)
        db_master.close()
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

        for name in torus_topo.satellites(self.graph):
            node = self.graph.nodes[name]
            ip = node.get("ip")
            if ip is not None:
                ip = format(ip)
            self.addHost(
                name,
                cls=FrrRouterNode,
                ip=ip,
                ospf=node["ospf"],
                vtysh=node["vtysh"],
                daemons=node["daemons"],
            )
            self.routers.append(name)

        for name in torus_topo.ground_stations(self.graph):
            node = self.graph.nodes[name]
            ip = node.get("ip")
            if ip is not None:
                ip = format(ip)
            self.addHost(name, ip=ip)
            station = GroundStation(name, node["uplinks"])
            self.ground_stations[name] = station

        # Create links between routers
        for name, edge in self.graph.edges.items():
            router1 = name[0]
            ip1 = edge["ip"][router1]
            intf1 = edge["intf"][router1]

            router2 = name[1]
            ip2 = edge["ip"][router2]
            intf2 = edge["intf"][router2]

            self.addLink(
                router1,
                router2,
                intfName1=intf1,
                intfName2=intf2,
                params1={"ip": format(ip1)},
                params2={"ip": format(ip2)},
            )

    def get_monitor_stats(self, net: mininet.net.Mininet):
        good_count: int = 0
        total_count: int = 0
        for name in self.routers:
            router = net.getNodeByName(name)
            db_working = mnet.pmonitor.open_db(router.working_db)
            good, total = mnet.pmonitor.get_status_count(db_working)
            db_working.close()
            good_count += good
            total_count += total
        return good_count, total_count

    def sample_stats(self, net: mininet.net.Mininet):
        good, total = self.get_monitor_stats(net)
        self.stat_samples.append((datetime.datetime.now(), good, total))
        if len(self.stat_samples) > 200:
            self.stat_samples.pop(0)

    def get_node_status_list(self, name: str, net: mininet.net.Mininet):
        router = net.getNodeByName(name)
        db_working = mnet.pmonitor.open_db(router.working_db)
        result = mnet.pmonitor.get_status_list(db_working)
        return result

    def get_stat_samples(self):
        return self.stat_samples

    def get_topo_graph(self) -> networkx.Graph:
        return self.graph

    def get_ring_list(self) -> list[list[str]]:
        return self.graph.graph["ring_list"]

    def get_router_list(self) -> list[tuple[str,str]]:
        result = []
        for name in torus_topo.satellites(self.graph):
            node = self.graph.nodes[name]
            ip = ""
            if node.get("ip") is not None:
                ip = format(node.get("ip"))
            else:
                ip = ""
            result.append((name, ip))
        return result

    def get_link_list(self) -> list[tuple[str,str,str]]:
        result = []
        for edge in self.graph.edges:
            node1 = edge[0]
            node2 = edge[1]
            ip_str = []
            for ip in self.graph.edges[node1, node2]["ip"].values():
                ip_str.append(format(ip))
            result.append((node1, node2, "-".join(ip_str)))
        return result

    def get_link(self, node1: str, node2: str):
        if self.graph.nodes.get(node1) is None:
            return f"{node1} does not exist"
        if self.graph.nodes.get(node2) is None:
            return f"{node2} does not exist"
        edge = self.graph.adj[node1].get(node2)
        if edge is None:
            return f"link {node1}-{node2} does not exist"
        return (node1, node2, edge["ip"][node1], edge["ip"][node2])

    def get_router(self, name: str, net: mininet.net.Mininet):
        if self.graph.nodes.get(name) is None:
            return f"{name} does not exist"
        result = {"name": name, "ip": self.graph.nodes[name].get("ip"), "neighbors": {}}
        for neighbor in self.graph.adj[name].keys():
            edge = self.graph.adj[name][neighbor]
            result["neighbors"][neighbor] = {
                "ip": edge["ip"][neighbor],
                "up": self.get_link_state(name, neighbor, net),
                "intf": edge["intf"][neighbor],
            }
        return result

    def get_ground_stations(self) -> list[GroundStation]:
        return [x for x in self.ground_stations.values()]

    def set_link_state(
        self, node1: str, node2: str, state_up: bool, net: mininet.net.Mininet
    ):
        if self.graph.nodes.get(node1) is None:
            return f"{node1} does not exist"
        if self.graph.nodes.get(node2) is None:
            return f"{node2} does not exist"
        adj = self.graph.adj[node1].get(node2)
        if self.graph.adj[node1].get(node2) is None:
            return f"{node1} to {node2} does not exist"
        self._config_link_state(node1, node2, state_up, net)
        return None

    def _config_link_state(
        self, node1: str, node2: str, state_up: bool, net: mininet.net.Mininet
    ):
        state = "up" if state_up else "down"
        net.configLinkStatus(node1, node2, state)

    def get_link_state(self, node1: str, node2: str, net: mininet.net.Mininet) -> tuple[bool, bool]:
        n1 = net.nameToNode.get(node1)
        n2 = net.nameToNode.get(node2)
        links = net.linksBetween(n1, n2)
        if len(links) > 0:
            link = links[0]
            return link.intf1.isUp(), link.intf2.isUp()

        return False, False

    def set_station_uplinks(
        self, station_name: str, uplinks: list[simapi.UpLink], net: mininet.net.Mininet
    ) -> bool:
        if not station_name in self.ground_stations:
            return False
        station = self.ground_stations[station_name]

        # Determine which links should be removed
        next_list = [uplink.sat_node for uplink in uplinks]
        for sat_name in station.sat_links():
            if sat_name not in next_list:
                print(f"Remove uplink {station.name} - {sat_name}")
                uplink = station.remove_uplink(sat_name)
                self._remove_link(station_name, sat_name, uplink.ip_pool_entry.network, net)

        # Add any new links
        for link in uplinks:
            if not station.has_uplink(link.sat_node):
                print(f"Add uplink {station.name}- {link.sat_node}")
                uplink = station.add_uplink(link.sat_node, link.distance)
                if uplink is not None:
                    self._create_link(
                        station_name,
                        link.sat_node,
                        uplink.ip_pool_entry.network,
                        uplink.ip_pool_entry.ip1,
                        uplink.ip_pool_entry.ip2,
                        net,
                        )
        self._update_default_route(station, net)
        return True

    def _create_link(
        self,
        node1: str,
        node2: str,
        ip_nw: ipaddress.IPv4Network,
        ip1: ipaddress.IPv4Interface,
        ip2: ipaddress.IPv4Interface,
        net: mininet.net.Mininet,
    ):
        # Create the link
        net.addLink(
            node1, node2, params1={"ip": format(ip1)}, params2={"ip": format(ip2)}
        )
        # Advertise network in OSPF
        frr_node = net.getNodeByName(node2)
        # TODO: add
        # station = self.ground_stations[station_name]
        # ip route {ground station ip /32} {ground station pool ip}",
        # ospf redistribute static in base config
        # Note: could also use redistribute connected - maybe better
        #frr_node.frr_config_commands(
        #        [ "router ospf",
        #         f"network {format(ip_nw)} area 0.0.0.0"])

    def _remove_link(self, station_name: str, sat_name: str, ip_nw: ipaddress.IPv4Network, net: mininet.net.Mininet) -> None:
        station_node = net.getNodeByName(station_name)
        sat_node = net.getNodeByName(sat_name)
        # TODO: add no ip route for ground station
        #sat_node.frr_config_command(
        #        [ "router ospf", 
        #         f"no network {format(ip_nw)} area 0.0.0.0"])
        net.delLinkBetween(station_node, sat_node)

    def _update_default_route(self, station: GroundStation, net: mininet.net.Mininet) -> None:
        closest_uplink = None
        # Find closest uplink
        for uplink in station.uplinks:
            if closest_uplink is None:
                closest_uplink = uplink
            elif closest_uplink.distance < uplink.distance:
                closest_uplink = uplink
        
        # If the closest has changed, update the default route
        if closest_uplink is not None and not closest_uplink.default:
            # Clear current default
            for uplink in station.uplinks:
                uplink.default = False
            # Mark new default and set
            closest_uplink.default = True 
            station_node = net.getNodeByName(station.name)
            route = "via %s" % format(closest_uplink.ip_pool_entry.ip2.ip)
            print(f"set default route for {station.name} to {route}")
            station_node.setDefaultRoute(route)
 
class NetxTopoStub(NetxTopo):
    def __init__(self, graph: networkx.Graph):
        super(NetxTopoStub, self).__init__(graph)

    def get_monitor_stats(self, net: mininet.net.Mininet):
        good_count: int = random.randrange(20)
        total_count: int = random.randrange(20) + good_count
        return good_count, total_count

    def _create_link(
            self, node1: str, node2: str, ip_nw: ipaddress.IPv4Network, ip1: ipaddress.IPv4Interface, ip2: ipaddress.IPv4Interface, net: mininet.net.Mininet
    ):
        print(f"create link {node1}{format(ip1)} - {node2}:{format(ip2)}")
        pass

    def _remove_link(self, station_name: str, sat_name: str, ip_nw: ipaddress.IPv4Network, net: mininet.net.Mininet) -> None:
        print(f"remove link {station_name} - {sat_name}")
        pass

    def _update_default_route(self, station: GroundStation, net: mininet.net.Mininet) -> None:
        pass

    def _config_link_state(
        self, node1: str, node2: str, state_up: bool, net: mininet.net.Mininet
    ):
        pass

    def get_link_state(self, node1: str, node2: str, net: mininet.net.Mininet) -> tuple[bool,bool]:
        return True, True

    def get_node_status_list(self, name: str, net: mininet.net.Mininet):
        return []


if __name__ == "__main__":
    graph = torus_topo.create_network(8, 8)
    frr_config_topo.annotate_graph(graph)
    topo = NetxTopo(graph)
    topo.build()

    for name in torus_topo.satellites(graph):
        node = graph.nodes[name]
        print(node["ospf"])
        print()
