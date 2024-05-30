"""
Sample code to excercise skyfield functions 
on TLE data.
"""

from skyfield.api import EarthSatellite
from skyfield.api import load, wgs84
from skyfield.positionlib import Geocentric


def test_sat_functions():
    text = """
KUIPER-P2
1 58013U 23154A   24112.59759155  .00036225  00000+0  11739-2 0  9998
2 58013  29.9759 213.3677 0013412 240.3957 119.5332 15.30656097 30278
"""

    lines = text.strip().splitlines()
    sat = EarthSatellite(lines[1], lines[2], lines[0])
    print("Epoch")
    print(sat.epoch.utc_jpl())
    print()
    print("Geocentric Position")
    ts = load.timescale()
    geo = sat.at(ts.now())
    lat, lon = wgs84.latlon_of(geo)
    print(geo.position.km)
    print(f"Latitude: {lat}")
    print(f"Longitude: {lon}")
    print(f"Distance from center of earth: {geo.distance().km}km")


    print()
    print("Geo of 1au, 0, 0")
    geo = Geocentric([1, 0, 0], t=ts.now())
    lat, lon = wgs84.latlon_of(geo)
    print(geo.position.km)
    print(f"Latitude: {lat}")
    print(f"Longitude: {lon}")
    print(f"Distance: {geo.distance()}")

if __name__ == "__main__":
    test_sat_functions()
