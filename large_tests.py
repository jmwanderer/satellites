"""
Time consuming tests
"""
import unittest
import torus_topo

class TestCase(unittest.TestCase):
    def testTorusRouting(self):
        self.assertTrue(torus_topo.run_routing_test())

