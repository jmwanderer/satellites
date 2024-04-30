
from skyfield.api import EarthSatellite
from skyfield.api import load, wgs84

url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=gps-ops&FORMAT=tle"
satellites = load.tle_file(url)
print("Loadded %d satellites", len(satellites))

for sat in satellites:
    print(f"Name: {sat.name}")
    print("Epoch %s" % sat.epoch.utc_jpl())
    print("Geocentric Position")
    ts = load.timescale()
    geo = sat.at(ts.now()) 
    lat, lon = wgs84.latlon_of(geo)
    print(geo.position.km)
    print(f"Latitude: {lat}")
    print(f"Longitude: {lon}")
    print()



