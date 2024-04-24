"""
Load a TLE file and draw the Satellites, updating locations every 5 seconds.

"""

# TODO:
# - Click on a satellite and display information
# - smooth animation with posInterval?
# - allow time to run faster than 1:1


from dataclasses import dataclass
import datetime
import queue
import sys
import time
import threading

from direct.showbase.ShowBase import ShowBase
from direct.showbase.DirectObject import DirectObject
from direct.task import Task
from skyfield.api import load, wgs84
from skyfield.positionlib import Geocentric

@dataclass
class PositionUpdate:
    """Reports new positions for objects."""
    name: str
    position: tuple
    rotation: int
    time: datetime.datetime

done = False
def generate_positions(update_q: queue.Queue, sat_entries):
    ts = load.timescale()
    while not done:
        time_now = datetime.datetime.now(tz=datetime.UTC)
        # Generate earth rotation location
        sf_time = ts.from_datetime(time_now)
        geo = Geocentric([1, 0, 0],t=sf_time)
        #print("Earth geo: %s" % geo.position.km)
        lat, lon = wgs84.latlon_of(geo)
        #print(f"lat: {lat}, lon: {lon}")
        update = PositionUpdate("earth", (), lon.degrees, time_now)
        update_q.put(update)

        # Generate position for each satellite
        count = 0
        for sat in sat_entries:
            #print(f"Name: {sat.name}")
            geo = sat.at(sf_time) 
            lat, lon = wgs84.latlon_of(geo)
            #print(geo.position.km)
            #print(f"Latitude: {lat}")
            #print(f"Longitude: {lon}")
            #print()
            update = PositionUpdate(sat.name, geo.position.km, 0, time_now)
            update_q.put(update)
            count += 1
        print(f"generated locations for {count} satellites")
        time.sleep(5)


base = ShowBase()
class World(DirectObject):

    def __init__(self):
        base.disableMouse()  # disable mouse control of the camera
        base.camera.setHpr(0, 0, 0)  # Set the camera orientation

        # Time speed up factor for animation.
        self.speed = 1
        self.zoom = 8

        # Scale earth, satellites, and orbit
        self.sat_size_scale = 0.1  
        self.earth_size_scale = 10

        # Radius of earth 6373km
        # Orbit height above earch 500km
        # Scale orbit above the earth
        self.pos_scale = self.earth_size_scale / 6373
        self.satellites = {}
        self.sat_entries = []
        self.update_q = queue.Queue()
        self.setCameraPos()

    def setCameraPos(self):
        altitude = 6373 + self.zoom**2 * 500
        zoom = -altitude * self.pos_scale
        print(f"set camera y = {zoom}")
        if zoom > -self.earth_size_scale - 1:
            zoom = -self.earth_size_scale - 1
        base.camera.setPos(0, zoom, 0)  # Set the camera position (X, Y, Z)

    def setup_elements(self):
        # If you change this, delete gp.php
        # Kuiper
        url = "https://celestrak.org/NORAD/elements/gp.php?INTDES=2023-154"
        # GPS Satellites
        url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=gps-ops&FORMAT=tle"
        # Starlink
        url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle"
        # Space stations
        url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle"
        self.sat_entries = load.tle_file(url)
        print("Loaded %d satellites" % len(self.sat_entries))
        self.loadElements()
        self.accept('q', sys.exit)
        self.accept('arrow_up', self.moveUp)
        self.accept('arrow_down', self.moveDown)
        self.accept('arrow_right', self.moveRight)
        self.accept('arrow_left', self.moveLeft)
        self.accept('+', self.zoomIn)
        self.accept('-', self.zoomOut)
        self.heading = 0
        self.pitch = 0
        self.t = threading.Thread(target=generate_positions, 
                                  args=[self.update_q, self.sat_entries],
                                  daemon=True)
        self.t.start()
        base.taskMgr.add(self.gLoop,'gloop')
    

    def setView(self):
        self.base.setHpr(self.heading, self.pitch, 0)

    def zoomIn(self):
        if self.zoom > 1:
            self.zoom -= 1
            self.setCameraPos()

    def zoomOut(self):
        self.zoom += 1
        self.setCameraPos()

    def moveUp(self):
        self.pitch -= 30
        self.setView()

    def moveDown(self):
        self.pitch += 30
        self.setView()

    def moveLeft(self):
        self.heading -= 30
        self.setView()

    def moveRight(self):
        self.heading += 30
        self.setView()

    def loadElements(self):
        """
        Create all of the nodes for the animation.
        """

        # Create nodes used to incline the orbit and rotate.
        # Pivots are nodes that change heading for rotation.
        # 40 orbits of 40 satellites
        self.base = base.render.attachNewNode('base')

        for sat_entry in self.sat_entries:
            sat = base.loader.loadModel("models/planet_sphere")
            sat.reparentTo(self.base)
            sat.setScale(self.sat_size_scale)
            self.satellites[sat_entry.name]  = sat
        # Load the Earth
        self.earth = base.loader.loadModel("models/planet_sphere")
        earth_tex = base.loader.loadTexture("models/earth_1k_tex.jpg")
        self.earth.setTexture(earth_tex, 1)
        self.earth.reparentTo(self.base)
        self.earth.setScale(self.earth_size_scale)

    def processPositionUpdate(self, update: PositionUpdate):
        if update.name == "earth":
            # Calculate a magic number that seems to align with the image we use??
            rotate = 163 - update.rotation
            print("rotate earth: %d degrees" % rotate)
            self.earth.setHpr(rotate,0,0)
            return
        
        satellite = self.satellites[update.name]
        x = update.position[0] * self.pos_scale
        y = update.position[1] * self.pos_scale
        z = update.position[2] * self.pos_scale
        satellite.setPos(x, y, z)

    def gLoop(self,task):
        while not self.update_q.empty():
            self.processPositionUpdate(self.update_q.get())
        return Task.cont



w = World()
w.setup_elements()
base.run()
