import pandas as pd
import numpy as np
from pathlib import Path


def load_data(bridges_path: str, roads_path: str):
    """Load bridges (Excel) and roads (CSV) datasets."""
    bridges = pd.read_excel(bridges_path)
    roads = pd.read_csv(roads_path)
    return bridges, roads


def filter_road(bridges: pd.DataFrame, roads: pd.DataFrame, road_name: str):
    """Return only rows belonging to the selected road."""
    bridges_r = bridges[bridges["road"] == road_name].copy()
    roads_r = roads[roads["road"] == road_name].copy()
    return bridges_r, roads_r


def prepare_road_links(roads_r: pd.DataFrame):
    roads_r = roads_r.sort_values("chainage").reset_index(drop=True)
    roads_r["start_km"] = roads_r["chainage"]
    roads_r["end_km"] = roads_r["chainage"].shift(-1)
    roads_r = roads_r[roads_r["road"] == roads_r["road"].shift(-1)].copy()
    roads_r["model_type"] = "link"
    roads_r["length"] = roads_r["end_km"] - roads_r["start_km"]
    roads_r["condition"] = pd.NA
    return roads_r[
        ["road", "model_type", "name", "lat", "lon", "length", "condition", "start_km", "end_km"]
    ]


def prepare_bridges(bridges_r: pd.DataFrame):
    bridges_r = bridges_r.copy()
    bridges_r["length_km"] = bridges_r["length"] / 1000
    bridges_r["start_km"] = bridges_r["chainage"] - bridges_r["length_km"] / 2
    bridges_r["end_km"] = bridges_r["chainage"] + bridges_r["length_km"] / 2
    bridges_r["model_type"] = "bridge"
    bridges_r["length"] = bridges_r["length_km"]
    bridges_r = bridges_r.rename(columns={"LRPName": "lrp"})
    return bridges_r[
        ["road", "model_type", "name", "lat", "lon", "length", "condition", "start_km", "end_km"]
    ]


def split_links_at_bridges(roads_r: pd.DataFrame, bridges_r: pd.DataFrame):
    cut_points = sorted(
        set(bridges_r["start_km"].tolist() + bridges_r["end_km"].tolist())
    )
    bridge_intervals = [(row.start_km, row.end_km) for _, row in bridges_r.iterrows()]

    def inside_bridge(s, e):
        for bs, be in bridge_intervals:
            if s >= bs and e <= be:
                return True
        return False

    split_links = []
    for _, row in roads_r.iterrows():
        s, e = row["start_km"], row["end_km"]
        internal_cuts = [x for x in cut_points if s < x < e]
        boundaries = [s] + internal_cuts + [e]
        for i in range(len(boundaries) - 1):
            seg_start = boundaries[i]
            seg_end = boundaries[i + 1]
            if inside_bridge(seg_start, seg_end):
                continue
            new_row = row.copy()
            new_row["start_km"] = seg_start
            new_row["end_km"] = seg_end
            new_row["length"] = seg_end - seg_start
            split_links.append(new_row)

    return pd.DataFrame(split_links)


def process_road_network(bridges_path, roads_path, road_name):
    bridges, roads = load_data(bridges_path, roads_path)
    bridges_r, roads_r = filter_road(bridges, roads, road_name)
    roads_r = prepare_road_links(roads_r)
    bridges_r = prepare_bridges(bridges_r)
    roads_r = split_links_at_bridges(roads_r, bridges_r)
    return pd.concat([roads_r, bridges_r], ignore_index=True)


def get_main_road_for_side_road(road_name: str):
    for main_road in ("N1", "N2"):
        suffix = road_name[len(main_road):]
        if road_name.startswith(main_road) and road_name != main_road and suffix.isdigit():
            return main_road
    return None


def select_roads_for_network(
    roads: pd.DataFrame,
    main_roads=("N1", "N2"),
    min_side_road_length_km=25.0,
    roads_exclude=None,
):
    roads_exclude = set() if roads_exclude is None else set(roads_exclude)
    road_lengths = roads.groupby("road")["chainage"].max()

    selected_side_roads = []
    for road_name, length_km in road_lengths.items():
        main_road = get_main_road_for_side_road(road_name)
        if main_road is None or road_name in roads_exclude:
            continue
        if length_km > min_side_road_length_km:
            selected_side_roads.append({
                "road": road_name,
                "main_road": main_road,
                "length_km": float(length_km),
            })

    side_roads_df = pd.DataFrame(selected_side_roads)
    if not side_roads_df.empty:
        side_roads_df = side_roads_df.sort_values("road").reset_index(drop=True)

    roads_to_use = sorted((set(main_roads) | set(side_roads_df.get("road", []))) - roads_exclude)
    return roads_to_use, side_roads_df


def find_side_road_connections(
    roads: pd.DataFrame,
    side_roads_df: pd.DataFrame,
    threshold_deg=0.02,
):
    connection_rows = []

    for side_road in side_roads_df.itertuples(index=False):
        side_road_df = roads[roads["road"] == side_road.road].sort_values("chainage").reset_index(drop=True)
        main_road_df = roads[roads["road"] == side_road.main_road].sort_values("chainage").reset_index(drop=True)
        endpoints = [side_road_df.iloc[0], side_road_df.iloc[-1]]

        best_connection = None
        for endpoint_row in endpoints:
            lat = float(endpoint_row["lat"])
            lon = float(endpoint_row["lon"])
            dists = np.sqrt((main_road_df["lat"] - lat) ** 2 + (main_road_df["lon"] - lon) ** 2)
            closest_idx = dists.idxmin()
            closest = main_road_df.loc[closest_idx]

            connection = {
                "road": side_road.road,
                "main_road": side_road.main_road,
                "length_km": side_road.length_km,
                "side_chainage": float(endpoint_row["chainage"]),
                "side_lat": lat,
                "side_lon": lon,
                "main_chainage": float(closest["chainage"]),
                "main_lat": float(closest["lat"]),
                "main_lon": float(closest["lon"]),
                "distance_deg": float(dists.loc[closest_idx]),
            }

            if best_connection is None or connection["distance_deg"] < best_connection["distance_deg"]:
                best_connection = connection

        best_connection["connection_type"] = (
            "direct" if best_connection["distance_deg"] < threshold_deg else "snapped"
        )
        connection_rows.append(best_connection)

    if not connection_rows:
        return pd.DataFrame(columns=[
            "road", "main_road", "length_km", "side_chainage", "side_lat", "side_lon",
            "main_chainage", "main_lat", "main_lon", "distance_deg", "connection_type"
        ])

    return pd.DataFrame(connection_rows).sort_values("road").reset_index(drop=True)


def find_junctions(raw_roads_selected: pd.DataFrame, threshold_deg=0.02, forced_connections=None):
    """
    Find all junction points between roads.
    For each junction, add BOTH:
      - an intersection node (for NetworkX routing)
      - a sourcesink node (so vehicles can be generated/removed there)
    at the same location on each road involved.
    forced_connections can add explicit side-road to trunk-road junctions,
    including snapped connections when no direct intersection exists.
    """
    roads_pts = raw_roads_selected.copy()
    roads_pts = roads_pts.sort_values(["road", "chainage"]).reset_index(drop=True)

    rows = []
    added = set()
    sosi_counter = [1]

    def add_junction(road, lat, lon, chainage):
        key = (road, round(lat, 3), round(lon, 3))
        if key in added:
            return
        added.add(key)

        rows.append({
            "road": road,
            "model_type": "intersection",
            "name": pd.NA,
            "lat": lat,
            "lon": lon,
            "length": 0.001,
            "condition": pd.NA,
            "start_km": chainage,
            "end_km": chainage
        })

        # If junction is at an road endpoint, also add a sourcesink at the same location for vehicle generation/removal
        if chainage == 0 or np.isclose(chainage, roads_pts[roads_pts["road"] == road]["chainage"].max()):

            rows.append({
                "road": road,
                "model_type": "sourcesink",
                "name": f"SoSi{sosi_counter[0]}",
                "lat": lat,
                "lon": lon,
                "length": 0.001,
                "condition": pd.NA,
                "start_km": chainage,
                "end_km": chainage
            })
            sosi_counter[0] += 1

    for road in roads_pts["road"].unique():
        road_df = roads_pts[roads_pts["road"] == road].sort_values("chainage")

        for endpoint_row in [road_df.iloc[0], road_df.iloc[-1]]:
            lat, lon = endpoint_row["lat"], endpoint_row["lon"]

            other = roads_pts[roads_pts["road"] != road]
            dist = np.sqrt((other["lat"] - lat)**2 + (other["lon"] - lon)**2)
            min_dist = dist.min()

            if min_dist < threshold_deg:
                add_junction(road, lat, lon, endpoint_row["chainage"])
                closest_idx = dist.idxmin()
                closest = other.loc[closest_idx]
                add_junction(closest["road"], closest["lat"], closest["lon"], closest["chainage"])

    if forced_connections is not None and not forced_connections.empty:
        for connection in forced_connections.itertuples(index=False):
            add_junction(connection.road, connection.side_lat, connection.side_lon, connection.side_chainage)

            if connection.connection_type == "direct":
                main_lat = connection.main_lat
                main_lon = connection.main_lon
            else:
                main_lat = connection.side_lat
                main_lon = connection.side_lon

            add_junction(connection.main_road, main_lat, main_lon, connection.main_chainage)

    if not rows:
        return pd.DataFrame(columns=[
            "road", "model_type", "name", "lat", "lon",
            "length", "condition", "start_km", "end_km"
        ])

    return pd.DataFrame(rows)


def add_sourcesinks_from_raw_roads(
    raw_roads_selected: pd.DataFrame,
    threshold_deg=0.02,
    start_counter=1,
    connected_endpoints=None,
):
    """
    Create sourcesink rows at open road endpoints (not connected to any other road).
    """
    roads_pts = raw_roads_selected.copy()
    roads_pts = roads_pts.sort_values(["road", "chainage"]).reset_index(drop=True)

    sosi_rows = []
    sosi_counter = start_counter
    connected_endpoint_keys = set()

    if connected_endpoints is not None and not connected_endpoints.empty:
        connected_endpoint_keys = {
            (row.road, round(float(row.side_chainage), 6))
            for row in connected_endpoints.itertuples(index=False)
        }

    for road in roads_pts["road"].unique():
        road_df = roads_pts[roads_pts["road"] == road].sort_values("chainage")

        for endpoint_row in [road_df.iloc[0], road_df.iloc[-1]]:
            endpoint_key = (road, round(float(endpoint_row["chainage"]), 6))
            if endpoint_key in connected_endpoint_keys:
                continue

            lat, lon = endpoint_row["lat"], endpoint_row["lon"]
            other = roads_pts[roads_pts["road"] != road]
            dist = np.sqrt((other["lat"] - lat)**2 + (other["lon"] - lon)**2)

            if dist.min() >= threshold_deg:
                sosi_rows.append({
                    "road": road,
                    "model_type": "sourcesink",
                    "name": f"SoSi{sosi_counter}",
                    "lat": lat,
                    "lon": lon,
                    "length": 0.001,
                    "condition": pd.NA,
                    "start_km": endpoint_row["chainage"],
                    "end_km": endpoint_row["chainage"]
                })
                sosi_counter += 1

    return pd.DataFrame(sosi_rows)


def finalize_network(network_df: pd.DataFrame):
    """
    Final formatting:
    - remove duplicate rows by road + model_type + rounded lat/lon
    - sort each road's nodes by chainage, sourcesinks first at same chainage
    - convert km to meters
    - assign unique ids
    - keep required columns
    """
    full_network = network_df.copy()

    full_network["lat_round"] = full_network["lat"].round(4)
    full_network["lon_round"] = full_network["lon"].round(4)

    full_network = full_network.drop_duplicates(
        subset=["road", "model_type", "lat_round", "lon_round"]
    ).reset_index(drop=True)

    full_network = full_network.drop(columns=["lat_round", "lon_round"])

    type_order = {"sourcesink": 0, "intersection": 1, "bridge": 2, "link": 3}
    full_network["type_order"] = full_network["model_type"].map(type_order).fillna(3)

    full_network = full_network.sort_values(
        ["road", "start_km", "type_order"], na_position="first"
    ).reset_index(drop=True)

    full_network = full_network.drop(columns=["type_order"])

    # Convert km to meters
    full_network["length"] = full_network["length"] * 1000

    # Assign unique IDs
    full_network["id"] = range(1_000_000, 1_000_000 + len(full_network))

    full_network = full_network[
        ["road", "id", "model_type", "condition", "name", "lat", "lon", "length"]
    ]

    return full_network


# ------------------------------------------------------------
# MAIN SCRIPT
# ------------------------------------------------------------

data_path = Path(__file__).resolve().parents[1] / "data"
(data_path / "processed").mkdir(exist_ok=True)

bridges = pd.read_excel(data_path / "raw" / "BMMS_overview.xlsx")
roads = pd.read_csv(data_path / "raw" / "_roads3.csv")

# Main roads are always included. Side roads are selected from the N1xx/N2xx naming rule.
MAIN_ROADS = ("N1", "N2")
MIN_SIDE_ROAD_LENGTH_KM = 25.0

# # Roads to explicitly exclude even if they match the side-road rule
# ROADS_EXCLUDE = {"N8"}
ROADS_EXCLUDE = None

threshold_deg = 0.02  # ~2 km, same as find_junctions

# 1. Select roads from the N1/N2 trunk roads and their long-enough N1xx/N2xx side roads.
roads_to_use, selected_side_roads = select_roads_for_network(
    roads,
    main_roads=MAIN_ROADS,
    min_side_road_length_km=MIN_SIDE_ROAD_LENGTH_KM,
    roads_exclude=ROADS_EXCLUDE,
)

side_road_connections = find_side_road_connections(
    roads,
    selected_side_roads,
    threshold_deg=threshold_deg,
)

print("Roads included in network:", roads_to_use)
if side_road_connections.empty:
    print("No qualifying N1xx/N2xx side roads found.")
else:
    print("\nSelected side-road connections:")
    print(
        side_road_connections[
            ["road", "main_road", "length_km", "distance_deg", "connection_type"]
        ].to_string(index=False)
    )

raw_roads_selected = roads[roads["road"].isin(roads_to_use)].copy()

# 2. Process each road's bridges and links
all_networks = []
for road in roads_to_use:
    net = process_road_network(
        data_path / "raw" / "BMMS_overview.xlsx",
        data_path / "raw" / "_roads3.csv",
        road
    )
    all_networks.append(net)

base_network = pd.concat(all_networks, ignore_index=True)

# 3. Add junction nodes (intersection + sourcesink pairs) and open-end sourcesinks
junction_nodes = find_junctions(
    raw_roads_selected,
    threshold_deg=threshold_deg,
    forced_connections=side_road_connections,
)
junction_sosi_count = junction_nodes[junction_nodes["model_type"] == "sourcesink"]["name"].nunique()

sourcesink_nodes = add_sourcesinks_from_raw_roads(
    raw_roads_selected,
    threshold_deg=threshold_deg,
    start_counter=junction_sosi_count + 1,
    connected_endpoints=side_road_connections,
)

print(f"Junction nodes (intersections + sourcesinks): {len(junction_nodes)}")
print(f"Open-end sourcesinks: {len(sourcesink_nodes)}")

full_network = pd.concat(
    [base_network, junction_nodes, sourcesink_nodes],
    ignore_index=True
)

# 4. Finalize
full_network = finalize_network(full_network)

print(f"\nNetwork summary:")
print(full_network["model_type"].value_counts().to_string())

# 5. Save
full_network.to_csv(data_path / "processed" / "network_AS3.csv", index=False)
print("\nNetwork saved to data/processed/network_AS3.csv")
