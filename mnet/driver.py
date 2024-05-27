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

    def add_event(self, event: str):
        self.events.append(event)

    def run_time(self) -> datetime.timedelta:
        now = datetime.datetime.now()
        return now - self.start_time 


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
    context = get_context()
    router = context.netxTopo.get_router(node, context.mn_net)
    print("loaded router")
    for neighbor in router["neighbors"]:
        intf1_state = intf_state(router["neighbors"][neighbor]["up"][0])
        intf2_state = intf_state(router["neighbors"][neighbor]["up"][1])
        router["neighbors"][neighbor]["up"]  = (intf1_state, intf2_state)

    return templates.TemplateResponse(
            request=request,
            name="router.html",
            context={"router": router}
            )

@app.get("/view/link/{node1}/{node2}", response_class=HTMLResponse)
def view_link(request: Request, node1: str, node2: str):
    context = get_context()
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
    context = get_context()
    state = "up" if link.up else "down"
    context.add_event(f"set link {link.node1_name} - {link.node2_name} {state}")
    err = context.netxTopo.set_link_state(link.node1_name, link.node2_name,
                                          link.up, context.mn_net)
    if err is not None:
        return {"error": err}
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

def invoke_shutdown():
    context = get_context()
    context.server.should_exit = True
    context.server.force_exit = True
 
