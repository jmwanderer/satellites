"""
Simulate location changes in a satellite network in real time.

Generate events for:
    - Satellite position change
    - horizontal links down above and below a critical latitude
    - new / break  connections to ground stations
    - new / break connections to end hosts

"""

from dataclasses import dataclass
import sys
import datetime
import time

import torus_topo

import networkx
from skyfield.api import load, wgs84 # type: ignore
from skyfield.api import EarthSatellite # type: ignore
from skyfield.positionlib import Geocentric # type: ignore
from skyfield.units import Angle # type: ignore


@dataclass
class Satellite:
    """Represents an instance of a satellite"""

    name: str
    earth_sat: EarthSatellite
    geo: Geocentric = None
    lat: Angle = 0
    lon: Angle = 0
    inter_plane_status: bool = True
    prev_inter_plane_status: bool = True


class SatSimulation:
    """
    Runs real time to update satellite positions
    """

    # Time slice for simulation
    TIME_SLICE = 10

    def __init__(self, graph: networkx.Graph):
        self.graph = graph
        self.ts = load.timescale()
        self.satellites: list[Satellite] = []
        for node in graph.nodes:
            orbit = graph.nodes[node]["orbit"]
            ts = load.timescale()
            l1, l2 = orbit.tle_format()
            earth_satellite = EarthSatellite(l1, l2, node, ts)
            satellite = Satellite(node, earth_satellite)
            self.satellites.append(satellite)

    def updatePositions(self, future_time: datetime.datetime):
        for satellite in self.satellites:
            sfield_time = self.ts.from_datetime(future_time)
            satellite.geo = satellite.earth_sat.at(sfield_time)
            lat, lon = wgs84.latlon_of(satellite.geo)
            satellite.lat = lat
            satellite.lon = lon
            print(f"{satellite.name} Lat: {satellite.lat}, Lon: {satellite.lon}")

    def updateInterPlaneStatus(self):
        inclination = self.graph.graph["inclination"]
        for satellite in self.satellites:
            # Track if state changed
            satellite.prev_inter_plane_status = satellite.inter_plane_status
            if satellite.lat.degrees > (inclination - 2) or satellite.lat.degrees < (
                -inclination + 2
            ):
                # Above the threashold for inter plane links to connect
                satellite.inter_plane_status = False
                print(f"{satellite.name} ISL down")
            else:
                satellite.inter_plane_status = True

    def run(self):
        current_time = datetime.datetime.now(tz=datetime.UTC)
        slice_delta = datetime.timedelta(seconds=SatSimulation.TIME_SLICE)
        while True:
            future_time = current_time + slice_delta
            print(f"update positions for {future_time}")
            self.updatePositions(future_time)
            self.updateInterPlaneStatus()
            sleep_delta = future_time - datetime.datetime.now(tz=datetime.UTC)
            print("sleep")
            time.sleep(sleep_delta.seconds)
            current_time = future_time


def run(num_rings: int, num_routers: int) -> None:
    graph = torus_topo.create_network(num_rings, num_routers)
    sim: SatSimulation = SatSimulation(graph)
    sim.run()


def usage():
    print("Usage: sim_sat <num rings> <routers-per-ring>")
    print("<rings> - number of rings in the topology, 1 - 20")
    print("<routers-per-ring> - number of routers in each ring, 1 - 20")


if __name__ == "__main__":
    if len(sys.argv) != 1 and len(sys.argv) != 3:
        usage()
        sys.exit(-1)

    num_rings = 4
    num_routers = 4

    if len(sys.argv) > 1:
        try:
            num_rings = int(sys.argv[1])
            num_routers = int(sys.argv[2])
        except:
            usage()
            sys.exit(-1)

    if num_rings < 1 or num_rings > 30 or num_routers < 1 or num_routers > 30:
        usage()
        sys.exit(-1)

    print(f"Running {num_rings} rings with {num_routers} per ring")
    run(num_rings, num_routers)
