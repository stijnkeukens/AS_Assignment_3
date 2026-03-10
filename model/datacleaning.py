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


def find_junctions(raw_roads_selected: pd.DataFrame, threshold_deg=0.02):
    """
    Find all junction points between roads.
    For each junction, add BOTH:
      - an intersection node (for NetworkX routing)
      - a sourcesink node (so vehicles can be generated/removed there)
    at the same location on each road involved.
    """
    roads_pts = raw_roads_selected.copy()
    roads_pts = roads_pts.sort_values(["road", "chainage"]).reset_index(drop=True)

    rows = []
    added = set()
    sosi_counter = [1]  # list so the nested function can modify it

    def add_junction(road, lat, lon, chainage):
        key = (road, round(lat, 3), round(lon, 3))
        if key in added:
            return
        added.add(key)

        # Intersection node — used by NetworkX for routing
        rows.append({
            "road": road,
            "model_type": "intersection",
            "name": pd.NA,
            "lat": lat,
            "lon": lon,
            "length": 0.02,
            "condition": pd.NA,
            "start_km": chainage,
            "end_km": chainage
        })

        # Sourcesink node at same location — vehicles can start/end here
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
                # Junction on this road's endpoint
                add_junction(road, lat, lon, endpoint_row["chainage"])
                # Junction on closest point of the other road
                closest_idx = dist.idxmin()
                closest = other.loc[closest_idx]
                add_junction(closest["road"], closest["lat"], closest["lon"], closest["chainage"])

    if not rows:
        return pd.DataFrame(columns=[
            "road", "model_type", "name", "lat", "lon",
            "length", "condition", "start_km", "end_km"
        ])

    return pd.DataFrame(rows)


def add_sourcesinks_from_raw_roads(raw_roads_selected: pd.DataFrame, threshold_deg=0.02, start_counter=1):
    """
    Create sourcesink rows at open road endpoints (not connected to any other road).
    """
    roads_pts = raw_roads_selected.copy()
    roads_pts = roads_pts.sort_values(["road", "chainage"]).reset_index(drop=True)

    sosi_rows = []
    sosi_counter = start_counter

    for road in roads_pts["road"].unique():
        road_df = roads_pts[roads_pts["road"] == road].sort_values("chainage")

        for endpoint_row in [road_df.iloc[0], road_df.iloc[-1]]:
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

    # Round lat/lon for dedup
    full_network["lat_round"] = full_network["lat"].round(4)
    full_network["lon_round"] = full_network["lon"].round(4)

    full_network = full_network.drop_duplicates(
        subset=["road", "model_type", "lat_round", "lon_round"]
    ).reset_index(drop=True)

    full_network = full_network.drop(columns=["lat_round", "lon_round"])

    # Sort: sourcesinks first, then intersections, then bridges, then links
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

# 1. Find all N-roads longer than 25 km
road_lengths = roads.groupby("road")["chainage"].max()
long_roads = road_lengths[road_lengths > 25].index.tolist()
long_roads = [r for r in long_roads if r.startswith("N")]

# 2. Find roads connected to N1/N2 using rounded coordinates
roads["lat_round"] = roads["lat"].round(2)
roads["lon_round"] = roads["lon"].round(2)

n1n2_points = roads[roads["road"].isin(["N1", "N2"])][["lat_round", "lon_round"]].drop_duplicates()

connected_roads = roads.merge(
    n1n2_points,
    on=["lat_round", "lon_round"],
    how="inner"
)["road"].unique().tolist()

# 3. Keep only long connected N-roads + always N1 and N2
roads_to_use = [r for r in long_roads if r in connected_roads]
roads_to_use = sorted(list(set(roads_to_use + ["N1", "N2"])))

print("Roads included in network:", roads_to_use)

raw_roads_selected = roads[roads["road"].isin(roads_to_use)].copy()

# 4. Process each road's bridges and links
all_networks = []
for road in roads_to_use:
    net = process_road_network(
        data_path / "raw" / "BMMS_overview.xlsx",
        data_path / "raw" / "_roads3.csv",
        road
    )
    all_networks.append(net)

base_network = pd.concat(all_networks, ignore_index=True)

# 5. Add junction nodes (intersection + sourcesink pairs) and open-end sourcesinks
junction_nodes = find_junctions(raw_roads_selected)
junction_sosi_count = junction_nodes[junction_nodes["model_type"] == "sourcesink"]["name"].nunique()

sourcesink_nodes = add_sourcesinks_from_raw_roads(
    raw_roads_selected,
    start_counter=junction_sosi_count + 1
)

print(f"Junction nodes (intersections + sourcesinks): {len(junction_nodes)}")
print(f"Open-end sourcesinks: {len(sourcesink_nodes)}")

full_network = pd.concat(
    [base_network, junction_nodes, sourcesink_nodes],
    ignore_index=True
)

# 6. Finalize
full_network = finalize_network(full_network)

print(f"\nNetwork summary:")
print(full_network["model_type"].value_counts().to_string())

# 7. Save
full_network.to_csv(data_path / "processed" / "network_AS3.csv", index=False)
print("\nNetwork saved to data/processed/network_AS3.csv")