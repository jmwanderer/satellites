import datetime
from contextlib import contextmanager
import threading
import time

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import uvicorn
import mininet

from mnet.frr_topo import FrrSimRuntime
import simapi


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
    def __init__(self, frrt: FrrSimRuntime, uvicorn_server):
        self.frrt = frrt
        self.server = uvicorn_server
        self.events = []
        self.start_time = datetime.datetime.now()
        self.lock = threading.Lock()

    def add_event(self, event: str):
        self.events.append((datetime.datetime.now(), event))
        if len(self.events) > 1000:
            self.events.pop(0)

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
        yield global_context
    finally:
        global_context.release()


def background_thread():
    while True:
        time.sleep(20)
        with get_context() as context:
            context.frrt.sample_stats()


app = FastAPI()


def run(frrt: FrrSimRuntime):
    global global_context

    config = uvicorn.Config(
        app, host="0.0.0.0", port=8000, log_level="info", loop="asyncio"
    )
    server = uvicorn.Server(config=config)
    global_context = NetxContext(frrt, server)
    # Consider using a uvicorn facility to do this instead
    bg_thread = threading.Thread(target=background_thread)
    bg_thread.daemon = True
    bg_thread.start()
    server.run()


templates = Jinja2Templates(directory="mnet/templates")


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    with get_context() as context:
        rings = context.frrt.get_topo_graph().graph["rings"]
        current_time = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
        run_time = str(context.run_time())
        ring_nodes = context.frrt.get_topo_graph().graph["ring_nodes"]
        good, total = context.frrt.get_monitor_stats()
        routers = context.frrt.get_router_list()
        links = context.frrt.get_link_list()
        src_stats = context.frrt.get_stat_samples()
        stats = []
        for stat in src_stats:
            stats.append(
                (stat[0].time().isoformat(timespec="seconds"), stat[1], stat[2])
            )
        events = []
        for entry in context.events[-min(len(context.events), 10) :]:
            events.append((entry[0].time().isoformat(timespec="seconds"), entry[1]))
        stations = context.frrt.get_ground_stations()

    info = {
        "rings": rings,
        "ring_nodes": ring_nodes,
        "stats_good": good,
        "stats_total": total,
        "current_time": current_time,
        "run_time": run_time,
        "routers": routers,
        "links": links,
        "events": events,
        "stats": stats,
        "stations": stations,
    }
    return templates.TemplateResponse(
        request=request, name="main.html", context={"info": info}
    )


def intf_state(up: bool):
    return "up" if up else "down"


@app.get("/view/router/{node}", response_class=HTMLResponse)
def view_router(request: Request, node: str):
    with get_context() as context:
        router = context.frrt.get_router(node)
        status_list = context.frrt.get_node_status_list(node)
        ring_list = context.frrt.get_ring_list()
        for neighbor in router["neighbors"]:
            intf1_state = intf_state(router["neighbors"][neighbor]["up"][0])
            intf2_state = intf_state(router["neighbors"][neighbor]["up"][1])
            router["neighbors"][neighbor]["up"] = (intf1_state, intf2_state)

    return templates.TemplateResponse(
        request=request,
        name="router.html",
        context={"router": router, "ring_list": ring_list, "status_list": status_list},
    )


@app.get("/view/link/{node1}/{node2}", response_class=HTMLResponse)
def view_link(request: Request, node1: str, node2: str):
    with get_context() as context:
        link = context.frrt.get_link(node1, node2)
        up1, up2 = context.frrt.get_link_state(node1, node2)

    return templates.TemplateResponse(
        request=request,
        name="link.html",
        context={
            "link": link,
            "intf1_state": intf_state(up1),
            "intf2_state": intf_state(up2),
        },
    )



@app.put("/link")
def set_link(link: simapi.Link):
    with get_context() as context:
        state = "up" if link.up else "down"
        context.add_event(f"set link {link.node1_name} - {link.node2_name} {state}")
        err = context.frrt.set_link_state(
            link.node1_name, link.node2_name, link.up
        )
    if err is not None:
        return {"error": err}
    return {"status": "OK"}

@app.put("/uplinks")
def set_uplinks(uplinks: simapi.UpLinks):
    with get_context() as context:
        print(f"set uplinks for {uplinks.ground_node}")
        # TODO: add ground stations and uplinks to NxTopo
        # Add a call to set the uplinks which will diff and change the links
        context.frrt.set_station_uplinks(uplinks.ground_node, 
                                             uplinks.uplinks)
        return {"status": "OK"}


@app.get("/stats/total")
def stats_total():
    with get_context() as context:
        good, total = context.frrt.get_monitor_stats()
    return {"good_count": good, "toital_count": total}


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
