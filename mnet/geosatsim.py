#
# Geographic Satellite Simulator
#
# Simulate in real time specific events in a satellite network:
# Satellite position - based on TLE data specs
# - inclination, right acesion, revs / day, rev number
# Adjacent sattelite links up / down based on lattiude
# - send link down / link up events
# Groundstation and host connections
# - send ground station and host connect / disconnect events
#

# Args:
# - network size: rings / routers
# - driver interface: url of JSON API interface that accepts events
#
