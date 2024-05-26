from fastapi import FastAPI
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
    #uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")
    


@app.get("/")
def root():
    return {"message": "Hello World"}


@app.get("/stats/total")
def stats_total():
    context = get_context()
    good, total = context.netxTopo.get_monitor_stats(context.mn_net)
    return {"good_count": good,
            "toital_count": total }

@app.get("/shutdown")
async def shutdown():
    context = get_context()
    context.server.should_exit = True
    context.server.force_exit = True
    await context.server.shutdown()


