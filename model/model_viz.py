from mesa.visualization.ModularVisualization import ModularServer
from ContinuousSpace.SimpleContinuousModule import SimpleCanvas
from model import BangladeshModel
from components import Source, Sink, Bridge, Link, Intersection, Infra, SourceSink

"""
Run simulation with Visualization 
Print output at terminal
"""


# ---------------------------------------------------------------
def agent_portrayal(agent):
    """
    Define the animation method

    Only circles and rectangles are possible
    Both can be labelled
    """

    portrayal = {
        "Shape": "circle",
        "Filled": "true",
        "Color": "Khaki",
        "r": 2,
        "Layer": 0
    }

    if isinstance(agent, SourceSink):
        portrayal["Color"] = "green" if agent.vehicle_generated_flag else "red"
        portrayal["r"] = 6
        portrayal["Layer"] = 3

    elif isinstance(agent, Source):
        portrayal["Color"] = "green" if agent.vehicle_generated_flag else "red"
        portrayal["r"] = 6
        portrayal["Layer"] = 3

    elif isinstance(agent, Sink):
        portrayal["Color"] = "LightSkyBlue" if agent.vehicle_removed_toggle else "LightPink"
        portrayal["r"] = 6
        portrayal["Layer"] = 3

    elif isinstance(agent, Intersection):
        portrayal["Color"] = "DeepPink"
        portrayal["r"] = 5
        portrayal["Layer"] = 2

    elif isinstance(agent, Bridge):
        if agent.vehicle_count > 0:
            portrayal["Color"] = "dodgerblue"
            portrayal["r"] = min(agent.vehicle_count * 2 + 2, 6)
        else:
            portrayal["Color"] = "gray"
            portrayal["r"] = 2
        portrayal["Layer"] = 1

    elif isinstance(agent, Link):
        portrayal["Color"] = "Tan"
        if agent.vehicle_count > 0:
            portrayal["r"] = min(agent.vehicle_count * 2 + 2, 6)
        else:
            portrayal["r"] = 2
        portrayal["Layer"] = 0

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

canvas_width = 500
canvas_height = 500

space = SimpleCanvas(agent_portrayal, canvas_width, canvas_height)

server = ModularServer(BangladeshModel,
                       [space],
                       "Transport Model Demo",
                       {"seed": 1234567,"scenario": 0})

# The default port
server.port = 8521
server.launch()