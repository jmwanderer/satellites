"""
Geographic Satellite Simulator
Simulate location changes in a satellite network in real time.

Simulate in real time specific events in a satellite network:
Generate events for:
    - Satellite position - based on TLE data specs
    - horizontal links down above and below a critical latitude
    - new / break  connections to ground stations
    - new / break connections to end hosts
"""

from dataclasses import dataclass, field
import configparser
import sys
import datetime
import time

import torus_topo
import simclient

import networkx
from skyfield.api import load, wgs84 # type: ignore
from skyfield.api import EarthSatellite # type: ignore
from skyfield.positionlib import Geocentric # type: ignore
from skyfield.toposlib import GeographicPosition # type: ignore
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

@dataclass
class Uplink:
    """Represents a link between the ground and a satellite"""
    satellite_name: str
    ground_name: str
    distance: int

@dataclass
class GroundStation:
    """Represents an instance of a ground station"""
    name: str
    position: GeographicPosition
    uplinks: list[Uplink] = field(default_factory=list)


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
        self.ground_stations: list[GroundStation] = []
        self.client: simclient.Client = simclient.Client("http://127.0.0.0:8000")

        for name in torus_topo.ground_stations(graph):
            node = graph.nodes[name]
            position = wgs84.latlon(node[torus_topo.LAT], node[torus_topo.LON])
            ground_station = GroundStation(name, position)
            self.ground_stations.append(ground_station)

        for name in torus_topo.satellites(graph):
            orbit = graph.nodes[name]["orbit"]
            ts = load.timescale()
            l1, l2 = orbit.tle_format()
            earth_satellite = EarthSatellite(l1, l2, name, ts)
            satellite = Satellite(name, earth_satellite)
            self.satellites.append(satellite)

    def updatePositions(self, future_time: datetime.datetime):
        sfield_time = self.ts.from_datetime(future_time)
        for satellite in self.satellites:
            satellite.geo = satellite.earth_sat.at(sfield_time)
            lat, lon = wgs84.latlon_of(satellite.geo)
            satellite.lat = lat
            satellite.lon = lon
            print(f"{satellite.name} Lat: {satellite.lat}, Lon: {satellite.lon}")

    @staticmethod
    def nearby(ground_station: GroundStation, satellite: Satellite) -> bool:
        return (satellite.lon.degrees > ground_station.position.longitude.degrees - 15 and
                satellite.lon.degrees < ground_station.position.longitude.degrees + 15 and
                satellite.lat.degrees > ground_station.position.latitude.degrees - 10 and 
                satellite.lat.degrees < ground_station.position.latitude.degrees + 10)
 
    def updateUplinkStatus(self, future_time: datetime.datetime):
        """
        Update the links between ground stations and satellites
        """
        sfield_time = self.ts.from_datetime(future_time)
        for ground_station in self.ground_stations:
            ground_station.uplinks = [] 
            for satellite in self.satellites:
                # Calculate az for close satellites
                if SatSimulation.nearby(ground_station, satellite):
                    difference = satellite.earth_sat - ground_station.position
                    topocentric = difference.at(sfield_time)
                    alt, az, d = topocentric.altaz()
                    if alt.degrees > 35:
                        uplink = Uplink(satellite.name, ground_station.name, d.km)
                        ground_station.uplinks.append(uplink)
                        print(f"{satellite.name} Lat: {satellite.lat}, Lon: {satellite.lon}")
                        print(f"{ground_station.name} Lat: {ground_station.position.latitude}, Lon: {ground_station.position.longitude}")
                        print(f"ground {ground_station.name}, sat {satellite.name}: {alt}, {az}, {d.km}")

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
            else:
                satellite.inter_plane_status = True

    def send_updates(self):
        for satellite in self.satellites:
            if satellite.prev_inter_plane_status != satellite.inter_plane_status:
                for neighbor in self.graph.adj[satellite.name]: 
                    if self.graph.edges[satellite.name, neighbor]["inter_ring"]:
                        self.client.set_link_state(satellite.name, neighbor, satellite.inter_plane_status)
        
        for ground_station in self.ground_stations:
            links = []
            for uplink in ground_station.uplinks:
                links.append((uplink.satellite_name, int(uplink.distance)))
            self.client.set_uplinks(ground_station.name, links)

    def run(self):
        current_time = datetime.datetime.now(tz=datetime.timezone.utc)
        slice_delta = datetime.timedelta(seconds=SatSimulation.TIME_SLICE)
        while True:
            future_time = current_time + slice_delta
            print(f"update positions for {future_time}")
            self.updatePositions(future_time)
            self.updateUplinkStatus(future_time)
            self.updateInterPlaneStatus()
            sleep_delta = future_time - datetime.datetime.now(tz=datetime.timezone.utc)
            print("sleep")
            time.sleep(sleep_delta.seconds)
            self.send_updates()
            current_time = future_time


def run(num_rings: int, num_routers: int, ground_stations: bool) -> None:
    graph = torus_topo.create_network(num_rings, num_routers, ground_stations)
    sim: SatSimulation = SatSimulation(graph)
    sim.run()


def usage():
    print("Usage: sim_sat [config-file]")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        usage()
        sys.exit(-1)
        
    parser = configparser.ConfigParser()
    parser['network'] = {}
    try:
        if len(sys.argv) == 2:
            parser.read(sys.argv[1])
    except Exception as e:
        print(str(e))
        usage()
        sys.exit(-1)

    num_rings = parser['network'].getint('rings', 4)
    num_routers = parser['network'].getint('routers', 4)
    ground_stations = parser['network'].getboolean('ground_stations', False)

    if num_rings < 1 or num_rings > 30 or num_routers < 1 or num_routers > 30:
        print("Ring or router count out of supported range")
        sys.exit(-1)

    print(f"Running {num_rings} rings with {num_routers} per ring, ground stations {ground_stations}")
    run(num_rings, num_routers, ground_stations)
