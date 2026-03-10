from mesa.visualization.ModularVisualization import ModularServer
from ContinuousSpace.SimpleContinuousModule import SimpleCanvas
from model import BangladeshModel
from components import Source, Sink, Bridge, Link, Intersection, Infra

"""
Run simulation with Visualization 
Print output at terminal
"""


# ---------------------------------------------------------------
def agent_portrayal(agent):
    """
    Define the animation methode

    Only circles and rectangles are possible
    Both can be labelled
    """

    # define shapes
    portrayal = {
        "Shape": "circle",  # rect | circle
        "Filled": "true",
        "Color": "Khaki",
        "r": 2
        # "w": max(agent.population / 100000 * 4, 4),  # for "Shape": "rect"
        # "h": max(agent.population / 100000 * 4, 4)
    }

    if isinstance(agent, Source):
        if agent.vehicle_generated_flag:
            portrayal["Color"] = "green"
        else:
            portrayal["Color"] = "red"

    elif isinstance(agent, Sink):
        if agent.vehicle_removed_toggle:
            portrayal["Color"] = "LightSkyBlue"
        else:
            portrayal["Color"] = "LightPink"

    elif isinstance(agent, Link):
        portrayal["Color"] = "Tan"

    elif isinstance(agent, Intersection):
        portrayal["Color"] = "DeepPink"

    elif isinstance(agent, Bridge):
        # Only turn blue when vehicles are actually on the bridge
        if agent.vehicle_count > 0:
            portrayal["Color"] = "dodgerblue"
        else:
            portrayal["Color"] = "gray"

    if isinstance(agent, (Source, Sink)):
        portrayal["r"] = 5
    elif isinstance(agent, Infra):
        # Only scale up size when vehicles are present; stay small (r=2) otherwise
        if agent.vehicle_count > 0:
            portrayal["r"] = min(agent.vehicle_count * 2 + 2, 6)
        else:
            portrayal["r"] = 2

    # define text labels
    if isinstance(agent, Infra) and agent.name != "":
        portrayal["Text"] = ""
        portrayal["Text_color"] = "DarkSlateGray"

    return portrayal


# ---------------------------------------------------------------
"""
Launch the animation server 
Open a browser tab 
"""

canvas_width = 400
canvas_height = 400

space = SimpleCanvas(agent_portrayal, canvas_width, canvas_height)

server = ModularServer(BangladeshModel,
                       [space],
                       "Transport Model Demo",
                       {"seed": 1234567})

# The default port
server.port = 8521
server.launch()