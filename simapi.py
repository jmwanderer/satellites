"""
Definitions for elements of the Simulator API

The server side of the API is implemented in mnet/driver.py
The client side is implemented in mnet/client.py
"""

from pydantic import BaseModel

class Link(BaseModel):
    node1_name: str
    node2_name: str
    up: bool

class UpLink(BaseModel):
    sat_node: str
    distance: int

class UpLinks(BaseModel):
    ground_node: str
    uplinks: list[UpLink]



