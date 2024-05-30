"""
Sample code to download the TLE info of the GPS satellites and
dump stats to the terminal.
"""

from skyfield.api import load, wgs84
import os

def load_gps_sats():
    url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=gps-ops&FORMAT=tle"
    if not os.path.exists("cache"):
        os.mkdir("cache")

    # Note, will not reload after the first time until cache is cleared.
    satellites = load.tle_file(url, filename="cache/gps-ops.tle")
    print("Loadded %d satellites", len(satellites))

    for sat in satellites:
        print(f"Name: {sat.name}")
        print("Epoch %s" % sat.epoch.utc_jpl())
        ts = load.timescale()
        geo = sat.at(ts.now())
        lat, lon = wgs84.latlon_of(geo)
        height = wgs84.height_of(geo)
        print("Geocentric Position")
        print(geo.position.km)
        print(f"Latitude: {lat}")
        print(f"Longitude: {lon}")
        print(f"Height: {height.km:.2f}km")
        print()


if __name__ == "__main__":
    load_gps_sats()
