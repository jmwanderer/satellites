# Satellites
Scripts and programs for visualizing and modeling satellite orbits and
simulating satellite networks.

We use Panda3D to run an interactive 3D view of satellites oribiting around the 
earth, and use the Skyfield astronomy library to determin the position of
the satellites.

# Setup

For the basic set of scripts, we use Panda#D, networkx, and skyfield.

To run these, create and activate a Python virtual environment and use 
pip to install the dependencies.  In the base directory:

```
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
```

# Animate Ideal Orbits
We use Panda3d elements to simulate the orbits of a satellite 
network by creating 40 rotating disks inclined at 53 degrees and 
attaching spheres to the disks represent satellites.

Run an animation of a 40x40 LEO satellite conselation:

```
python animate_orbits.py
```

- Enter q to quit.
- Use arrow keys to change the view

![screenshot](orbits.png)

# Calculate Actual Satellite Positions
We use the Skyfield astronomy library to calcualte the position of
earth satellites.


# Animate Real Satellite Groups
Use TLE files to position and update groups of Satellites in real time

```
python orbit_set.py starlink
```

The availabel constellations are:
- starlink
- stations (space stations)
- kuiper
- GPS

You can control the image display:
- + and - top zoom in and out (shift + does not yet work)
- arrow keys to change the orientation of the world
- q to quit

![screenshot](starlink.png)

# Network Topology and Routes
Build a topology and routing tables
```
python network.py

```

# Satellite Positions
Generate satellite positions with Skyfield and CTSC
```
python sat_pos_samples.py
```

# Network Topology
Utilities to explore a possible network topology of a satellite network where each
satellite is a router with 4 ports connecting to neighboring satellites in a torus 
topology.

- torus_topo: Generate a networkx graph of a connected set of rings (default 40x40)
- frr_config_topo: Generate FRR network configurations for a networkx topology
- test_large_frr: Generate, configure, and exercise a large torus topology

Exercise a large torus topology, generate routes, and trace paths:
```
python torus_topo.py
```

Exercise FRR network configuration generation on a small network:
```
python frr_config_topo.py
```

Generate a large torus topology and generate FRR network config information
```
python test_large_frr.py
```


# Mininet Emulation
Run an mininet emulation of an FRR based network toplogy.

Must be run as root in a Mininet/FRR package.
See [mininet_frr](http://github.com/jmwanderer/mininet_frr)


```
sudo python -m mnet.run_mn
```

The network currently just runs an OSPF daemon on each node to exchange.
Possible plans include:
- Adding network link up and down events as satellites move in orbit
- Adding hosts to connect as staellites move overhead
- Adding an OF controller to handle host connectivity
- Using an agent on host and satellites for control and connectivity testing


# Useful Information

- [Skyfield Library](https://rhodesmill.org/skyfield/earth-satellites.html)
- [Network topology design at 27,000 km.hour](https://satnetwork.github.io)
- [Celes Track Satellite Catalog](https://celestrak.org/satcat/search.php)
- [NetworkX](https://networkx.org/documentation/stable/index.html)

