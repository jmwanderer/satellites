"""
Client to drive the JSON api implemented in driver.py
"""
import requests


class Client:
    def __init__(self, url: str) -> None:
        self.url = url

    def set_link_state(self, node1: str, node2: str, up: bool) -> None:
        try:
            print(f"send link state {node1}, {node2}, state up {up}")
            r = requests.put(self.url, data={'node1_name': node1, 'node2_name': node2, 'up': up})
        except requests.exceptions.ConnectionError as e:
            print(e)
            pass

#client = Client("http://localhost:5000")
#client.set_link_state("R1", "R2", True)