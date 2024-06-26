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
    """
    References key simulation resources and protects against multi-threaded access.
    """
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
    """"
    Serialize access to the global context
    """
    try:
        global_context.aquire()
        yield global_context
    finally:
        global_context.release()

run_thread: bool = True
def background_thread():
    """
    Drive background collection of monitoring stats.
    """
    while run_thread:
        if run_thread:
            with get_context() as context:
                context.frrt.sample_stats()
        time.sleep(20)


app = FastAPI()

def run(frrt: FrrSimRuntime):
    """
    Start the control API
    """
    global global_context
    global run_thread

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
    run_thread = False


# Used with HTML templates to generate pages
templates = Jinja2Templates(directory="mnet/templates")


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    with get_context() as context:
        rings = context.frrt.get_topo_graph().graph["rings"]
        current_time = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
        run_time = str(context.run_time())
        ring_nodes = context.frrt.get_topo_graph().graph["ring_nodes"]
        routers = context.frrt.get_router_list()
        links = context.frrt.get_link_list()
        link_stats = {}
        link_stats["count"] = len(links)
        up_count = 0
        for link in links:
            up1, up2 = context.frrt.get_link_state(link[0], link[1])
            if up1 and up2:
                up_count += 1

        link_stats["up_count"] = up_count

        stat_samples = context.frrt.get_stat_samples()

        stats_dates = []
        stats_stable_fail = []
        stats_stable_ok = []
        stats_dynamic_fail = []
        stats_dynamic_ok = []

        for stat in stat_samples:
            stats_dates.append(stat[0].time().isoformat(timespec="seconds"))
            stats_stable_ok.append(stat[1])
            stats_stable_fail.append(stat[2] - stat[1])
            stats_dynamic_ok.append(stat[3])
            stats_dynamic_fail.append(stat[4] - stat[3])

        # dict: key name, value: list of up to five tuples. tuple[name,bool]
        ping_stats = context.frrt.get_last_five_stats()
        events = []
        for entry in context.events[-min(len(context.events), 10) :]:
            events.append((entry[0].time().isoformat(timespec="seconds"), entry[1]))
        stations = context.frrt.get_ground_stations()

    info = {
        "rings": rings,
        "ring_nodes": ring_nodes,
        "current_time": current_time,
        "run_time": run_time,
        "routers": routers,
        "link_stats": link_stats,
        "events": events,
        "stats_dates": stats_dates,
        "stats_stable_ok": stats_stable_ok,
        "stats_stable_fail": stats_stable_fail,
        "stats_dynamic_ok": stats_dynamic_ok,
        "stats_dynamic_fail": stats_dynamic_fail,
        "ping_stats": ping_stats,
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

@app.get("/view/station/{name}", response_class=HTMLResponse)
def view_station(request: Request, name: str):
    with get_context() as context:
        station = context.frrt.get_station(name)
        status_list = context.frrt.get_node_status_list(name)
        ring_list = context.frrt.get_ring_list()
    return templates.TemplateResponse(
        request=request,
        name="station.html",
        context={"station": station, "ring_list": ring_list, "status_list": status_list}
    )


@app.put("/link")
def set_link(link: simapi.Link):
    """
    Set link up or down
    """
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
    """
    Change the current set of uplinks for a ground station
    """
    with get_context() as context:
        print(f"set uplinks for {uplinks.ground_node}")
        # TODO: create an event in the event log?
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
