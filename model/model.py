from mesa import Model
from mesa.time import BaseScheduler
from mesa.space import ContinuousSpace
from components import Source, Sink, SourceSink, Bridge, Link, Intersection, Vehicle
import pandas as pd
from collections import defaultdict
import networkx as nx
import numpy as np
from pathlib import Path
import os


# ---------------------------------------------------------------
def set_lat_lon_bound(lat_min, lat_max, lon_min, lon_max, edge_ratio=0.02):
    """
    Set the HTML continuous space canvas bounding box (for visualization)
    give the min and max latitudes and Longitudes in Decimal Degrees (DD)

    Add white borders at edges (default 2%) of the bounding box
    """

    lat_edge = (lat_max - lat_min) * edge_ratio
    lon_edge = (lon_max - lon_min) * edge_ratio

    x_max = lon_max + lon_edge
    y_max = lat_min - lat_edge
    x_min = lon_min - lon_edge
    y_min = lat_max + lat_edge
    return y_min, y_max, x_min, x_max


# ---------------------------------------------------------------
class BangladeshModel(Model):
    """
    The main (top-level) simulation model

    One tick represents one minute; this can be changed
    but the distance calculation need to be adapted accordingly

    Class Attributes:
    -----------------
    step_time: int
        step_time = 1 # 1 step is 1 min

    path_ids_dict: defaultdict
        Key: (origin, destination)
        Value: the shortest path (Infra component IDs) from an origin to a destination

    sources: list
        all sources in the network

    sinks: list
        all sinks in the network

    """

    step_time = 1
    path = Path(__file__).resolve().parents[1] / "data" / "processed" / "network_AS3.csv"
    file_name = os.fspath(path)
    # file_name = '../data/processed/network_AS3.csv'

    def __init__(self, seed=None, scenario=None, x_max=500, y_max=500, x_min=0, y_min=0):
        super().__init__(seed=seed)
        self.schedule = BaseScheduler(self)
        self.running = True
        self.path_ids_dict = defaultdict(lambda: pd.Series(dtype=int))
        self.space = None
        self.sources = []
        self.sinks = []
        self.G = nx.DiGraph()
        self.scenario = scenario       # must be set before generate_model()
        self.travel_times = []         # records completed vehicle trips

        self.generate_model()

    def generate_model(self):
        """
        generate the simulation model according to the csv file component information

        Warning: the labels are the same as the csv column labels
        """

        df = pd.read_csv(self.file_name)

        roads = list(df["road"].unique())

        df_objects_all = []
        for road in roads:
            df_objects_on_road = df[df['road'] == road]

            if not df_objects_on_road.empty:
                df_objects_all.append(df_objects_on_road)

                # Build straight-line path_ids_dict entries (forward and backward)
                # Always reset_index to ensure 0-based sequential indexing
                path_ids = df_objects_on_road['id'].reset_index(drop=True)
                self.path_ids_dict[path_ids[0], path_ids.iloc[-1]] = path_ids
                self.path_ids_dict[path_ids[0], None] = path_ids

                path_ids_rev = path_ids[::-1].reset_index(drop=True)
                self.path_ids_dict[path_ids_rev[0], path_ids_rev.iloc[-1]] = path_ids_rev
                self.path_ids_dict[path_ids_rev[0], None] = path_ids_rev

                # Build NetworkX graph edges for this road (bidirectional)
                ids = df_objects_on_road['id'].tolist()
                lengths = df_objects_on_road['length'].tolist()
                for i in range(len(ids) - 1):
                    weight = lengths[i] if lengths[i] > 0 else 1.0
                    self.G.add_edge(ids[i], ids[i + 1], weight=weight)
                    self.G.add_edge(ids[i + 1], ids[i], weight=weight)

        # Store lat/lon for every node
        df_all = pd.concat(df_objects_all)
        node_coords = df_all.set_index('id')[['lat', 'lon']].to_dict('index')
        for node_id, coords in node_coords.items():
            if node_id in self.G.nodes:
                self.G.nodes[node_id]['lat'] = coords['lat']
                self.G.nodes[node_id]['lon'] = coords['lon']

        # Connect intersection/sourcesink nodes across roads that are geographically close
        threshold_deg = 0.02
        junction_types = {'intersection', 'sourcesink'}
        junction_nodes = df_all[df_all['model_type'].isin(junction_types)][['id', 'lat', 'lon', 'road']]

        for _, row1 in junction_nodes.iterrows():
            for _, row2 in junction_nodes.iterrows():
                if row1['id'] == row2['id']:
                    continue
                if row1['road'] == row2['road']:
                    continue
                dist = np.sqrt((row1['lat'] - row2['lat'])**2 + (row1['lon'] - row2['lon'])**2)
                if dist < threshold_deg:
                    self.G.add_edge(row1['id'], row2['id'], weight=0)
                    self.G.add_edge(row2['id'], row1['id'], weight=0)

        print(f"Graph: {self.G.number_of_nodes()} nodes, {self.G.number_of_edges()} edges")
        print(f"Connected components: {nx.number_weakly_connected_components(self.G)}")

        # put back to df with selected roads so that min and max can be easily calculated
        df = pd.concat(df_objects_all)
        y_min, y_max, x_min, x_max = set_lat_lon_bound(
            df['lat'].min(),
            df['lat'].max(),
            df['lon'].min(),
            df['lon'].max(),
            0.05
        )

        self.space = ContinuousSpace(x_max, y_max, True, x_min, y_min)

        for df in df_objects_all:
            for _, row in df.iterrows():

                model_type = row['model_type'].strip()
                agent = None

                name = row['name']
                if pd.isna(name):
                    name = ""
                else:
                    name = name.strip()

                if model_type == 'source':
                    agent = Source(row['id'], self, row['length'], name, row['road'])
                    self.sources.append(agent.unique_id)
                elif model_type == 'sink':
                    agent = Sink(row['id'], self, row['length'], name, row['road'])
                    self.sinks.append(agent.unique_id)
                elif model_type == 'sourcesink':
                    agent = SourceSink(row['id'], self, row['length'], name, row['road'])
                    self.sources.append(agent.unique_id)
                    self.sinks.append(agent.unique_id)
                elif model_type == 'bridge':
                    agent = Bridge(row['id'], self, row['length'], name, row['road'], row['condition'], row['lat'], row['lon'])
                elif model_type == 'link':
                    agent = Link(row['id'], self, row['length'], name, row['road'])
                elif model_type == 'intersection':
                    if not row['id'] in self.schedule._agents:
                        agent = Intersection(row['id'], self, row['length'], name, row['road'])

                if agent:
                    self.schedule.add(agent)
                    y = row['lat']
                    x = row['lon']
                    self.space.place_agent(agent, (x, y))
                    agent.pos = (x, y)

    def get_random_route(self, source):
        """
        Pick a random sink and return the shortest path from source to sink.
        Uses path_ids_dict as a cache — only computes via NetworkX if not cached.
        Retries with different sinks if no path found.
        """
        sinks = [s for s in self.sinks if s != source]
        self.random.shuffle(sinks)

        for sink in sinks:
            # Return cached path if available
            cached = self.path_ids_dict[source, sink]
            if len(cached) > 0:
                return cached.reset_index(drop=True)

            # Compute shortest path via NetworkX and cache it
            try:
                node_path = nx.shortest_path(self.G, source, sink, weight='weight')
                path_series = pd.Series(node_path, dtype=int).reset_index(drop=True)
                self.path_ids_dict[source, sink] = path_series
                return path_series
            except nx.NetworkXNoPath:
                print(f"WARNING: No path found between {source} and {sink}, trying another sink.")
                continue

        print(f"WARNING: {source} has no reachable sinks.")
        return pd.Series(dtype=int)

    def get_route(self, source):
        """
        Get route for a vehicle — uses random routing via NetworkX shortest path.
        """
        return self.get_random_route(source)

    def get_straight_route(self, source):
        """
        Pick up a straight route given an origin (to end of road).
        """
        return self.path_ids_dict[source, None].reset_index(drop=True)

    def step(self):
        """
        Advance the simulation by one step.
        """
        self.schedule.step()

# EOF -----------------------------------------------------------