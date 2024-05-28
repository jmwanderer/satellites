import datetime
from contextlib import contextmanager
import threading

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from mnet.frr_topo import NetxTopo
import uvicorn
import mininet


# TODO:
# Open issue around context locking:
#   We block the calling thread with a lock. Is there a problem between
#   this and the asyncio model are are using with the server?
# Add a static page with 
# - status
# - shutdown links
# - data
# Surpress error on shutdown

class NetxContext:
    def __init__(self, topo: NetxTopo, 
                 mn: mininet.net.Mininet,
                 uvicorn_server):
        self.netxTopo: NetxTopo  = topo
        self.mn_net: mininet.net.Mininet = mn
        self.server = uvicorn_server
        self.events = []
        self.start_time = datetime.datetime.now()
        self.lock = threading.Lock()

    def add_event(self, event: str):
        self.events.append(event)

    def run_time(self) -> datetime.timedelta:
        now = datetime.datetime.now()
        return now - self.start_time 

    def aquire(self):
        self.lock.acquire()

    def release(self):
        self.lock.release()


global_context: NetxContext = None

@contextmanager
def get_context():
    try:
        global_context.aquire()
        yield global_context;
    finally:
        global_context.release()

app = FastAPI()

def run(topo: NetxTopo, mn: mininet.net.Mininet):
    global global_context

    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info", 
                            loop="asyncio")
    server = uvicorn.Server(config=config)
    global_context = NetxContext(topo, mn, server)
    server.run()
    

templates = Jinja2Templates(directory="mnet/templates")

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    with get_context() as context:
        rings = context.netxTopo.get_topo_graph().graph["rings"]
        current_time = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
        run_time = str(context.run_time())
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
            "run_time": run_time,
            "routers": routers,
            "links": links,
            "events": events
            }
    return templates.TemplateResponse(
            request=request, name="main.html", 
            context={"info": info}
            )

def intf_state(up: bool):
    return "up" if up else "down"

@app.get("/view/router/{node}", response_class=HTMLResponse)
def view_router(request: Request, node: str):
    with get_context() as context:
        router = context.netxTopo.get_router(node, context.mn_net)
        ring_list = context.netxTopo.get_ring_list()
        for neighbor in router["neighbors"]:
            intf1_state = intf_state(router["neighbors"][neighbor]["up"][0])
            intf2_state = intf_state(router["neighbors"][neighbor]["up"][1])
            router["neighbors"][neighbor]["up"]  = (intf1_state, intf2_state)

    return templates.TemplateResponse(
         request=request,
         name="router.html",
         context={"router": router, "ring_list": ring_list}
         )

@app.get("/view/link/{node1}/{node2}", response_class=HTMLResponse)
def view_link(request: Request, node1: str, node2: str):
    with get_context() as context:
        link = context.netxTopo.get_link(node1, node2)
        up1, up2 = context.netxTopo.get_link_state(node1, node2, context.mn_net)

    return templates.TemplateResponse(
            request=request, name="link.html",
            context={"link": link, 
                "intf1_state": intf_state(up1),
                "intf2_state": intf_state(up2) }
            )

class Link(BaseModel):
    node1_name: str
    node2_name: str
    up: bool


@app.put("/link")
def set_link(link: Link):
    with get_context() as context:
        state = "up" if link.up else "down"
        context.add_event(f"set link {link.node1_name} - {link.node2_name} {state}")
        err = context.netxTopo.set_link_state(link.node1_name, link.node2_name,
                                              link.up, context.mn_net)
    if err is not None:
        return {"error": err}
    return {"status": "OK" }


@app.get("/stats/total")
def stats_total():
    with get_context() as context:
        good, total = context.netxTopo.get_monitor_stats(context.mn_net)
    return {"good_count": good,
            "toital_count": total }

@app.get("/shutdown", response_class=HTMLResponse)
async def shutdown():
    with get_context() as context:
        context.server.should_exit = True
        context.server.force_exit = True
        await context.server.shutdown()
    return "<html><body><h1>Shutting down...</h1></body></html>"

def invoke_shutdown():
    with get_context() as context:
        context.server.should_exit = True
        context.server.force_exit = True
 
