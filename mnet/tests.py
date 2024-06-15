import unittest
import mnet.pmonitor
import frr_config_topo
import torus_topo
import mnet.frr_topo

class TestCase(unittest.TestCase):
    def testPMonitor(self):
        self.assertTrue(mnet.pmonitor.test())

    def testFrrTopo(self):
        # Create a networkx graph annoted with FRR configs
        graph = torus_topo.create_network(8, 8)
        frr_config_topo.annotate_graph(graph)
        frr_config_topo.dump_graph(graph)

        # Use the networkx graph to build a mininet topology
        topo = mnet.frr_topo.NetxTopo(graph)
        frrt = mnet.frr_topo.FrrSimRuntime(topo, None)
        frrt.start_routers()
        frrt.update_monitor_stats()
        frrt.sample_stats()
        frrt.update_monitor_stats()
        frrt.get_last_five_stats()
        routers = frrt.get_router_list()
        frrt.get_router(routers[0][0])
        links = frrt.get_link_list()
        frrt.get_link(links[0][0], links[0][1])
        frrt.get_node_status_list(routers[0][0])
        frrt.set_link_state(links[0][0], links[0][1], False)
        state1, state2 = frrt.get_link_state(links[0][0], links[0][1])
        self.assertFalse(state1 or state2)
        # TODO: add more calls here
        # set station uplinks
        frrt.stop_routers()

