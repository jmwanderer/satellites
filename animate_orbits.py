"""
Render a set of satellites in orbit around the earth.
40 orbits of 40 satellites at a ~53 degree incline to the equator.

Derived from: https://github.com/panda3d/panda3d/tree/master/samples/solar-system
"""

from direct.showbase.ShowBase import ShowBase

base = ShowBase()

from direct.gui.DirectGui import *
from direct.showbase.DirectObject import DirectObject
from panda3d.core import TextNode
from direct.task import Task

import sys
import math


class World(DirectObject):

    def __init__(self):
        base.disableMouse()  # disable mouse control of the camera
        base.camera.setPos(0, -45, 0)  # Set the camera position (X, Y, Z)
        base.camera.setHpr(0, 0, 0)  # Set the camera orientation
        # base.cam.setPos(0,-20,50)
        # base.cam.lookAt(render)

        # Seconds in a day for the earth rotation.
        self.day_len = 24 * 60 * 60

        # Sececonds for a satellite orbit.
        self.orbit_len = 90 * 60

        # Speed up factor for animation.
        self.speed = 90

        # Scale earth, satellites, and orbit
        self.sat_size_scale = 0.1
        self.earth_size_scale = 10

        # Radius of earth 6373km
        # Orbit height above earch 500km
        # Scale orbit above the earth
        self.orbitscale = self.earth_size_scale * (1 + 500 / 6373)
        #  Nodes for rotating around the earth
        self.pivots = []

        self.loadElements()
        self.rotateElements()
        base.taskMgr.add(self.gLoop, "gloop")
        self.accept("q", sys.exit)
        self.accept("arrow_up", self.moveUp)
        self.accept("arrow_down", self.moveDown)
        self.accept("arrow_right", self.moveRight)
        self.accept("arrow_left", self.moveLeft)
        self.heading = 0
        self.pitch = 0

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
        self.base = base.render.attachNewNode("base")
        orbits = 40
        for i in range(0, orbits):
            # We use one node, an oribt path to orient the orbit, setting the
            # degree of tilt and the orientation.
            orbit_path = self.base.attachNewNode(f"orbit_path_{i}")
            heading = (360 / orbits) * i
            orbit_path.setHpr(heading, 0, 53)

            # We create an additional node to simply rotate in the plane
            # set by the orbit path to which it is attached. We save this
            # node in order to run the rotation.
            orbit_pivot = orbit_path.attachNewNode(f"orbit_pivot_{i}")
            self.pivots.append(orbit_pivot)

            # Add satellites to the orbit.
            num_sats = 40
            # Radians between the satellites in the same orbit
            separation = math.pi * 2 / num_sats

            for sat_num in range(0, num_sats):
                sat = base.loader.loadModel("models/planet_sphere")
                sat.reparentTo(orbit_pivot)
                sat.setScale(self.sat_size_scale)
                rads = separation * sat_num
                if i % 2 == 0:
                    rads = rads + separation / 2
                x = math.sin(rads) * self.orbitscale
                y = math.cos(rads) * self.orbitscale
                sat.setPos(x, y, 0)

        # Load the Earth
        self.earth = base.loader.loadModel("models/planet_sphere")
        earth_tex = base.loader.loadTexture("models/earth_1k_tex.jpg")
        self.earth.setTexture(earth_tex, 1)
        self.earth.reparentTo(self.base)
        self.earth.setScale(self.earth_size_scale)
        self.earth.setHpr(0, 0, 0)

    def rotateElements(self):
        """
        Create all loops to drive the animation.
        """
        # Create a loop to rotate the earth
        self.day_period = self.earth.hprInterval(self.day_len / self.speed, (360, 0, 0))
        self.day_period.loop()

        # Create loops to rotate the orbits
        self.orbit_periods = []
        for orbit_pivot in self.pivots:
            orbit_period = orbit_pivot.hprInterval(
                self.orbit_len / self.speed, (360, 0, 0)
            )
            orbit_period.loop()
            self.orbit_periods.append(orbit_period)

    def gLoop(self, task):
        return Task.cont


w = World()
base.run()
