"""
Render a set of satellites in orbit around the earth.
40 orbits of 40 satellites at a ~53 degree incline to the equator.

Derived from: https://github.com/panda3d/panda3d/tree/master/samples/solar-system
"""

import sys
import datetime

from direct.showbase.ShowBase import ShowBase
from direct.showbase.DirectObject import DirectObject
from direct.task import Task
from skyfield.api import load, wgs84
from skyfield.positionlib import Geocentric


base = ShowBase()
class World(DirectObject):

    def __init__(self):
        base.disableMouse()  # disable mouse control of the camera
        base.camera.setPos(0, -60, 0)  # Set the camera position (X, Y, Z)
        base.camera.setHpr(0, 0, 0)  # Set the camera orientation

        # Time speed up factor for animation.
        self.speed = 1

        # Scale earth, satellites, and orbit
        self.sat_size_scale = 0.1  
        self.earth_size_scale = 10

        # Radius of earth 6373km
        # Orbit height above earch 500km
        # Scale orbit above the earth
        self.orbitscale = self.earth_size_scale * ( 1 + 500 / 6373)
        self.pos_scale = self.earth_size_scale / 6373
        self.satellites = []
        self.sat_entries = []
        self.positions = []
        self.time = datetime.datetime.now(tz=datetime.UTC)

    def setup_elements(self):
        url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=gps-ops&FORMAT=tle"
        url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle"
        url = "https://celestrak.org/NORAD/elements/gp.php?INTDES=2023-154"
        self.sat_entries = load.tle_file(url, reload=True)
        print("Loaded %d satellites", len(self.satellites))
        self.generate_positions()
        self.loadElements()
        self.rotateElements()
        self.accept('q', sys.exit)
        self.accept('arrow_up', self.moveUp)
        self.accept('arrow_down', self.moveDown)
        self.accept('arrow_right', self.moveRight)
        self.accept('arrow_left', self.moveLeft)
        self.heading = 0
        self.pitch = 0
    
    def generate_positions(self):
        # Gererate earth rotation location
        ts = load.timescale()
        time = ts.from_datetime(self.time)
        print("Geo of 1au, 0, 0")
        geo = Geocentric([1, 0, 0],t=time)
        lat, lon = wgs84.latlon_of(geo)
        print(geo.position.km)
        print(f"Latitude: {lat}")
        print(f"Longitude: {lon}")
        print(f"Distance: {geo.distance()}")
        self.earth_rotation = lon.degrees

        self.positions = []
        for sat in self.sat_entries:
            print(f"Name: {sat.name}")
            #print("Epoch %s" % sat.epoch.utc_jpl())
            #print("Geocentric Position")
            geo = sat.at(time) 
            lat, lon = wgs84.latlon_of(geo)
            print(geo.position.km)
            print(f"Latitude: {lat}")
            print(f"Longitude: {lon}")
            print()
            self.positions.append(geo.position.km)


    def setView(self):
        self.base.setHpr(self.heading, self.pitch, 0)

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

        for pos in self.positions:
            sat = base.loader.loadModel("models/planet_sphere")
            sat.reparentTo(self.base)
            sat.setScale(self.sat_size_scale)
            x = pos[0] * self.pos_scale
            y = pos[1] * self.pos_scale
            z = pos[2] * self.pos_scale
            sat.setPos(x, y, z)

        # Load the Earth
        self.earth = base.loader.loadModel("models/planet_sphere")
        earth_tex = base.loader.loadTexture("models/earth_1k_tex.jpg")
        self.earth.setTexture(earth_tex, 1)
        self.earth.reparentTo(self.base)
        self.earth.setScale(self.earth_size_scale)
        rotate = 180 - self.earth_rotation
        self.earth.setHpr(rotate,0,0)


    def rotateElements(self):
        """
        Create all loops to drive the animation.
        """
        # Create a loop to rotate the earth

w = World()
w.setup_elements()
base.run()
