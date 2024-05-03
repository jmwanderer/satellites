"""
Load a TLE file and draw the Satellites, updating locations every 5 seconds.

"""

# TODO:
# - Click on a satellite and display information
# - consider transforming arrow key input
# - control speed of time


from dataclasses import dataclass
import datetime
import math
import os
import queue
import sys
import time
import threading

from panda3d.core import PandaNode
from panda3d.core import TextNode
from panda3d.core import Point3
from panda3d.core import LVecBase3
from panda3d.core import CollisionNode
from panda3d.core import CollisionRay
from panda3d.core import CollisionTraverser
from panda3d.core import CollisionHandlerQueue
from panda3d.core import GeomNode
from direct.gui.DirectGui import OnscreenText
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
    now: bool
    time: datetime.datetime


done = False
TIME_RATE=60

# Global variables accessed by both threads, not protected by a mutex
# As currently structured, this should not cause a problem
last_time_sample: datetime.datetime = datetime.datetime.now(tz=datetime.UTC)
current_vtime: datetime.datetime = last_time_sample
vtime_paused: bool = False

def vtime_now() -> datetime.datetime:
    global last_time_sample
    global current_vtime
    global vtime_paused
    if not vtime_paused:
        # Calculate delta from last time sample and add to current time
        time_now = datetime.datetime.now(tz=datetime.UTC)
        delta = time_now - last_time_sample
        delta = delta * TIME_RATE
        last_time_sample = time_now
        current_vtime += delta
    return current_vtime

def pause_vtime():
    global vtime_paused
    vtime_paused = True

def resume_vtime():
    global last_time_sample
    global vtime_paused
    last_time_sample = datetime.datetime.now(tz=datetime.UTC)
    vtime_paused = False

def generate_positions(update_q: queue.Queue, sat_entries):
    ts = load.timescale()
    first = True
    future_seconds = min(60, 5 * TIME_RATE)

    while not done:
        time_now = vtime_now()
        delta = datetime.timedelta(seconds=future_seconds)
        time_future = time_now + delta
        earliest_time_future = time_future
        # Generate earth rotation location
        sf_time_now = ts.from_datetime(time_now)
        sf_time_future = ts.from_datetime(time_future)
        if first:
            geo = Geocentric([1, 0, 0], t=sf_time_now)
            lat, lon = wgs84.latlon_of(geo)
            # Calculate a magic number that seems to align with the image we use??
            rotate = 163 - lon.degrees
            update = PositionUpdate("earth", (), rotate, True, time_now)
            update_q.put(update)
    
        # Create future position
        geo = Geocentric([1, 0, 0], t=sf_time_future)
        lat, lon = wgs84.latlon_of(geo)
        # Calculate a magic number that seems to align with the image we use??
        rotate = 163 - lon.degrees
        update = PositionUpdate("earth", (), rotate, False, time_future)
        update_q.put(update)

        # Generate position for each satellite
        count = 0
        for sat in sat_entries:
            recalc_time = False

            # Pause every 100 calculations
            if count % 100 == 0:
                duration = 0
                if len(sat_entries) > 100:
                    # Spread out update generation throughout the interval.
                    duration = future_seconds * 50 / len(sat_entries) / TIME_RATE
                time.sleep(duration)
                recalc_time = True

            while update_q.qsize() > len(sat_entries):
                # Use backpressure on generating updates
                time.sleep(0)
                recalc_time = True

            if recalc_time:
               # Recalculate time values after potentially sleeping
               recalc_time = False
               time_now = vtime_now()
               time_future = time_now + delta
               sf_time_now = ts.from_datetime(time_now)
               sf_time_future = ts.from_datetime(time_future)
 
            #print(f"Gen Pos Name: {sat.name}")
            if first:
                # Create initial position
                geo = sat.at(sf_time_now)
                if not math.isnan(geo.position.km[0]):
                    update = PositionUpdate(sat.name, geo.position.km, 0, True, time_now)
                    update_q.put(update)

            # Create future position
            geo = sat.at(sf_time_future)
            if not math.isnan(geo.position.km[0]):
                update = PositionUpdate(sat.name, geo.position.km, 0, False, time_future)
                update_q.put(update)
            count += 1

        print(f"generated locations for {count} satellites")
        first = False
        print(f"vtime_now: {vtime_now()}")
        print(f"time_future: {earliest_time_future}")
        delta = (earliest_time_future - vtime_now())
        print(f"delta: {delta}")
        sleep_time = delta / TIME_RATE 
        print(f"sleep time {sleep_time}")
        sleep_seconds = max(0,sleep_time.total_seconds() - 0.2)
        print(f"sleep seconds {sleep_seconds}")
        time.sleep(sleep_seconds)


base = ShowBase()


class World(DirectObject):

    def __init__(self):
        base.disableMouse()  # disable mouse control of the camera
        base.camera.setHpr(0, 0, 0)  # Set the camera orientation

        # Setup collision detection for mouse clicks
        pickerNode = CollisionNode("mouseRay")
        pickerNP = base.camera.attachNewNode(pickerNode)
        pickerNode.setFromCollideMask(GeomNode.getDefaultCollideMask())
        self.pickerRay = CollisionRay()
        pickerNode.addSolid(self.pickerRay)
        self.collisionHandler = CollisionHandlerQueue()
        self.collisionTraverser = CollisionTraverser('mouseTraverser')
        base.cTrav = self.collisionTraverser
        self.collisionTraverser.addCollider(pickerNP, self.collisionHandler)

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
        self.satellites  : dict[str, PandaNode]= {}
        self.sat_intervals : dict[str, PositionUpdate] = {}
        self.sat_entries = []
        self.selected_sat = None
        self.update_q = queue.Queue()
        self.setCameraPos()
        self.time = OnscreenText(text="time", 
                                parent=base.a2dTopLeft,
                                align=TextNode.A_left, 
                                fg=(0,0,0,1),
                                pos=(0.1,-0.1),
                                scale=.07, style=1, mayChange=True)
        self.info = OnscreenText(text="", 
                                parent=base.a2dTopLeft,
                                align=TextNode.A_left, 
                                fg=(0,0,0,1),
                                pos=(0.1,-0.2),
                                scale=.07, style=1, mayChange=True)


    def setCameraPos(self):
        altitude = 6373 + self.zoom**2 * 500
        zoom = -altitude * self.pos_scale
        print(f"set camera y = {zoom}")
        if zoom > -self.earth_size_scale - 1:
            zoom = -self.earth_size_scale - 1
        base.camera.setPos(0, zoom, 0)  # Set the camera position (X, Y, Z)
        for name in self.satellites:
            self.satellites[name].setScale(self.get_sat_size_scale())
 
    URLS = { 
            "kuiper" : "https://celestrak.org/NORAD/elements/gp.php?INTDES=2023-154",
            "GPS" : "https://celestrak.org/NORAD/elements/gp.php?GROUP=gps-ops&FORMAT=tle",
            "stations" : "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle",
            "starlink" : "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle"
            }

    def setup_elements(self, selection):
        if selection not in World.URLS:
            print(f"{selection} unknown")
            print(list(World.URLS.keys()))
            sys.exit(-1)

        url = World.URLS[selection]

        print(f"loading constellation: {selection}")
        if not os.path.exists("cache"):
            os.mkdir("cache")

        # Reload if more than a week old.
        reload = False
        filename = f"cache/{selection}.tle"
        if os.path.exists(filename):
            reload = os.stat(filename).st_mtime < time.time() - 60 * 60 * 24 * 7
        self.sat_entries = load.tle_file(url, filename=filename, reload=reload)
        print("Loaded %d satellites" % len(self.sat_entries))

        self.loadElements()
        self.accept("q", sys.exit)
        self.accept("arrow_up", self.moveUp)
        self.accept("arrow_down", self.moveDown)
        self.accept("arrow_right", self.moveRight)
        self.accept("arrow_left", self.moveLeft)
        self.accept("+", self.zoomIn)
        self.accept("-", self.zoomOut)
        self.accept("space", self.togglePause)
        self.accept("mouse1", self.clickTarget)
        self.heading = 0
        self.pitch = 0
        self.t = threading.Thread(
            target=generate_positions,
            args=[self.update_q, self.sat_entries],
            daemon=True,
        )
        self.t.start()
        base.taskMgr.add(self.gLoop, "gloop")

    def setView(self):
        self.base.setHpr(self.heading, self.pitch, 0)

    def clickTarget(self):
        if base.mouseWatcherNode.hasMouse():
            mpos = base.mouseWatcherNode.getMouse()
            if self.selected_sat is not None:
                self.selected_sat.setColor(1,1,0,1.0)
                self.selected_sat = None
                self.info.setText("")

            self.pickerRay.setFromLens(base.camNode, mpos.x, mpos.y)
            self.collisionTraverser.traverse(base.render)

            if self.collisionHandler.getNumEntries() > 0:
                self.collisionHandler.sortEntries()
                pickedObj = self.collisionHandler.getEntry(0).getIntoNodePath()
                pickedObj = pickedObj.findNetTag('nametag')
                if not pickedObj.isEmpty():
                    self.info.setText(pickedObj.getTag('nametag'))
                    pickedObj.setColor(0,1,0,1.0)
                    self.selected_sat = pickedObj

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

    def togglePause(self):
        if vtime_paused:
            resume_vtime()
            for interval in self.sat_intervals.values():
                interval.resume()
        else:
            pause_vtime()
            for interval in self.sat_intervals.values():
                interval.pause()

    def get_sat_size_scale(self) -> int:
        # Increase scale with farther zoom settings. 
        # zoom 8 : multiplier = 1
        return self.sat_size_scale * (self.zoom / 8)

    def loadElements(self):
        """
        Create all of the nodes for the animation.
        """

        # Create nodes used to incline the orbit and rotate.
        # Pivots are nodes that change heading for rotation.
        # 40 orbits of 40 satellites
        self.base = base.render.attachNewNode("base")

        for sat_entry in self.sat_entries:
            sat = base.loader.loadModel("models/planet_sphere")
            sat.reparentTo(self.base)
            sat.setScale(self.get_sat_size_scale())
            sat.setTag('nametag', sat_entry.name)
            sat.setColor(1,1,0,1.0)
            self.satellites[sat_entry.name] = sat
        # Load the Earth
        self.earth = base.loader.loadModel("models/planet_sphere")
        earth_tex = base.loader.loadTexture("models/earth_1k_tex.jpg")
        self.earth.setTexture(earth_tex, 1)
        self.earth.reparentTo(self.base)
        self.earth.setScale(self.earth_size_scale)

    def processPositionUpdate(self, update: PositionUpdate):
        self.time.setText(vtime_now().isoformat(sep=' ', timespec="seconds"))
        if update.name == "earth":
            print("rotate earth: %d degrees" % update.rotation)
            if update.now:
                self.earth.setHpr(update.rotation, 0, 0)
            else:
                interval = self.sat_intervals.get(update.name)
                if interval is not None:
                    interval.pause()
                time_now = vtime_now()
                delta = update.time - time_now
                # Update position to avoid spinning the wrong way when going from 359 to 0
                current_rotation = self.earth.getHpr()[0]
                if current_rotation > update.rotation:
                    self.earth.setHpr(current_rotation - 360, 0, 0)
                interval = self.earth.hprInterval(delta.seconds / TIME_RATE, LVecBase3(update.rotation, 0, 0))
                interval.start()
                self.sat_intervals[update.name] = interval
 
            return

        satellite = self.satellites[update.name]
        x = update.position[0] * self.pos_scale
        y = update.position[1] * self.pos_scale
        z = update.position[2] * self.pos_scale
        if update.now:
            satellite.setPos(x, y, z)
        else:
            interval = self.sat_intervals.get(update.name)
            if interval is not None:
                interval.pause()
            time_now = vtime_now()
            delta = update.time - time_now
            interval = satellite.posInterval(delta.seconds / TIME_RATE, Point3(x, y, z))
            interval.start()
            self.sat_intervals[update.name] = interval
 

    def gLoop(self, task):
        while not self.update_q.empty() and not vtime_paused:
            self.processPositionUpdate(self.update_q.get())
        return Task.cont

selection = "kuiper"
if len(sys.argv) > 1:
    selection = sys.argv[1]
w = World()
w.setup_elements(selection)
base.run()
