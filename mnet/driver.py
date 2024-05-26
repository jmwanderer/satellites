import datetime

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from mnet.frr_topo import NetxTopo
import uvicorn
import mininet


# TODO:
# put a mutex around get_context
# Add a static page with 
# - status
# - shutdown links
# - data
# Catch ^c for a clean shutdown????
# Surpress error on shutdown

class NetxContext:
    def __init__(self, topo: NetxTopo, 
                 mn: mininet.net.Mininet,
                 uvicorn_server):
        self.netxTopo: NetxTopo  = topo
        self.mn_net: mininet.net.Mininet = mn
        self.server = uvicorn_server
        self.events = []

    def add_event(self, event: str):
        self.events.append(event)



context: NetxContext = None
def get_context():
    return context


app = FastAPI()

def run(topo: NetxTopo, mn: mininet.net.Mininet):
    global context

    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info", 
                            loop="asyncio")
    server = uvicorn.Server(config=config)
    context = NetxContext(topo, mn, server)
    server.run()
    

templates = Jinja2Templates(directory="mnet/templates")

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    context = get_context()
    rings = context.netxTopo.get_topo_graph().graph["rings"]
    current_time = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
    ring_nodes = context.netxTopo.get_topo_graph().graph["ring_nodes"]
    good, total = context.netxTopo.get_monitor_stats(context.mn_net)
    routers = context.netxTopo.get_router_list()
    links = context.netxTopo.get_link_list()
    events = context.events[:min(len(context.events), 10)]
    info = {"rings": rings,
            "ring_nodes": ring_nodes,
            "stats_good": good,
            "stats_total": total,
            "current_time": current_time,
            "routers": routers,
            "links": links,
            "events": events
            }
    return templates.TemplateResponse(
            request=request, name="main.html", 
            context={"info": info}
            )


class Link(BaseModel):
    name: str
    up: bool


@app.put("/link")
def set_link(link: Link):
    context = get_context()
    state = "up" if link.up else "down"
    context.add_event(f"set link {link.name} {state}")
    context.netxTopo.set_link_state(link.name, link.up)
    return {"status": "OK" }


@app.get("/stats/total")
def stats_total():
    context = get_context()
    good, total = context.netxTopo.get_monitor_stats(context.mn_net)
    return {"good_count": good,
            "toital_count": total }

@app.get("/shutdown", response_class=HTMLResponse)
async def shutdown():
    context = get_context()
    context.server.should_exit = True
    context.server.force_exit = True
    await context.server.shutdown()
    return "<html><body><h1>Shutting down...</h1></body></html>"


