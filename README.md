# Satellites
Scripts and programs for visualizing and modeling satellites.

# Setup
In the base directory:

```
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
```

# Animate Orbits
Run an animation of a 40x40 LEO satellite conselation.

```
python animate_orbits.py
```

- Enter q to quit.
- Use arrow keys to change the view

![screenshot](orbits.png)


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

# Useful Information

- [Skyfield Library](https://rhodesmill.org/skyfield/earth-satellites.html)
- [Network topology design at 27,000 km.hour](https://satnetwork.github.io)
- [Celes Track Satellite Catalog](https://celestrak.org/satcat/search.php)
- [NetworkX](https://networkx.org/documentation/stable/index.html)

