"""
Sample code to excercise skyfield functions 
on TLE data.
"""

from skyfield.api import EarthSatellite
from skyfield.api import load, wgs84
from skyfield.positionlib import Geocentric


# TLE entries for 3 satellites
starlink1="""
STARLINK-31857          
1 59843U 24097J   24152.50001157 -.00832730  00000+0 -40214-2 0  9991
2 59843  43.0045   5.2275 0001736 273.1057  88.8863 15.83654368  2541
"""
starlink2="""
STARLINK-30948          
1 58525U 23191T   24151.80439894  .00009599  00000+0  72464-3 0  9996
2 58525  43.0012  26.3148 0000805 284.9345  75.1408 15.02538244 28019
"""
kuiper = """
KUIPER-P2               
1 58013U 23154A   24151.54837047  .00017317  00000+0  50948-3 0  9990
2 58013  29.9766 310.4754 0012935 307.8864  52.0592 15.33643649 36251
"""

def dump_sat_info(tle_text: str) -> None:
    """
    Report current location based on TLE information.
    """
    # Load TLE data
    lines = tle_text.strip().splitlines()
    sat = EarthSatellite(lines[1], lines[2], lines[0])

    # Report static information
    print(f"Epoch: {sat.epoch.utc_jpl()}")
    print(f"Satellite name: {sat.name}")

    # Calculate current location
    ts = load.timescale()
    geo = sat.at(ts.now())

    # Convert from geo location to latitude, longitude, and hieght
    lat, lon = wgs84.latlon_of(geo)
    height = wgs84.height_of(geo)

    # Report location information
    print(f"Geocentric Position {geo.position.km}")
    print(f"Latitude: {lat}")
    print(f"Longitude: {lon}")
    print(f"Height above sea level: {height.km:.2f}km")
    print(f"Distance from center of earth: {geo.distance().km}km")
    print()



def test_sat_functions():
    dump_sat_info(starlink1)
    dump_sat_info(starlink2)
    dump_sat_info(kuiper)

if __name__ == "__main__":
    test_sat_functions()
