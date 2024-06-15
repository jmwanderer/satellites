import unittest
import torus_topo
import frr_config_topo
import sat_pos_samples
import gps_sats

class TestCase(unittest.TestCase):
    def testTorus(self):
        self.assertTrue(torus_topo.run_small_test())

    def testFrrConfig(self):
        self.assertTrue(frr_config_topo.test_config_graph())

    def testLargeFrrConfig(self):
        """
        Simple text to configure a 40x40 satellite network
        """
        graph = torus_topo.create_network()
        frr_config_topo.annotate_graph(graph)
        frr_config_topo.dump_graph(graph)

    def testSatPositionSamples(self):
        sat_pos_samples.test_sat_functions()

    def testGpsSats(self):
        gps_sats.load_gps_sats()
