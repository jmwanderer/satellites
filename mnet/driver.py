from fastapi import FastAPI
from mnet.frr_topo import NetxTopo
import uvicorn
import mininet

class NetxContext:
    def __init__(self, topo: NetxTopo, mn: mininet.net.Mininet):
        netxTopo: NetxTopo  = topo
        mn_net: mininet.net.Mininet mn

context: NetxContext = None
def get_context():
    return context


app = FastAPI()

def run(topo: NetxTopo, mn: mininet.net.Mininet):
    global context
    context = NetxContext(topo, mn)
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")
    


@app.get("/")
def root():
    return {"message": "Hello World"}


@app.get("/stats/total")
def stats_total():
    context = get_context()
    good, total = context.topo.get_monitor_stats(context.mn_net)
    return {"good_count": good,
            "toital_count": total }


