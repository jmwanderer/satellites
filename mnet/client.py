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
            url = f"{self.url}/link"
            state = "true" if up else "false"
            r = requests.put(url, 
                    json={'node1_name': node1, 'node2_name': node2, 'up': state})
            print(r.text)
        except requests.exceptions.ConnectionError as e:
            print(e)
            pass

#client = Client("http://localhost:5000")
#client.set_link_state("R1", "R2", True)
