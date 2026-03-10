import pandas as pd
from pathlib import Path

# Below follows the cleaning pipeline to get the correct dataset for further modelling

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

    roads_r = roads_r[roads_r["road"] == roads_r["road"].shift(-1)]

    roads_r["model_type"] = "link"
    roads_r["length"] = roads_r["end_km"] - roads_r["start_km"]

    return roads_r[[
        "road", "model_type", "name", "lat", "lon",
        "length", "start_km", "end_km"
    ]]


def prepare_bridges(bridges_r: pd.DataFrame):

    bridges_r = bridges_r.copy()

    bridges_r["length_km"] = bridges_r["length"] / 1000
    bridges_r["start_km"] = bridges_r["chainage"] - bridges_r["length_km"] / 2
    bridges_r["end_km"] = bridges_r["chainage"] + bridges_r["length_km"] / 2

    bridges_r["model_type"] = "bridge"
    bridges_r["length"] = bridges_r["length_km"]

    bridges_r = bridges_r.rename(columns={"LRPName": "lrp"})

    return bridges_r[[
        "road", "model_type", "name", "lat", "lon",
        "length", "condition", "start_km", "end_km"
    ]]


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


def build_full_network(roads_r: pd.DataFrame, bridges_r: pd.DataFrame):

    combined = pd.concat([roads_r, bridges_r], ignore_index=True)

    combined = combined.sort_values("start_km").reset_index(drop=True)

    if combined.loc[0, "model_type"] == "link":
        combined.loc[0, "model_type"] = "sourcesink"

    if combined.loc[combined.shape[0] - 1, "model_type"] == "link":
        combined.loc[combined.shape[0] - 1, "model_type"] = "sourcesink"

    combined["length"] = combined["length"] * 1000

    if "condition" not in combined.columns:
        combined["condition"] = pd.NA

    return combined


def process_road_network(bridges_path, roads_path, road_name):

    bridges, roads = load_data(bridges_path, roads_path)

    bridges_r, roads_r = filter_road(bridges, roads, road_name)

    roads_r = prepare_road_links(roads_r)
    bridges_r = prepare_bridges(bridges_r)

    roads_r = split_links_at_bridges(roads_r, bridges_r)

    full = build_full_network(roads_r, bridges_r)

    return full

def assign_intersections(network: pd.DataFrame):

    network = network.copy()

    network['lat_r'] = network['lat'].round(2)
    network['lon_r'] = network['lon'].round(2)

    # Keep only one entry per road per rounded coordinate to identify unique intersections
    one_per_road = network.sort_values('id').drop_duplicates(['road', 'lat_r', 'lon_r'])

    # A coordinate is an intersection if it belongs to more than one unique road
    mask = one_per_road.groupby(['lat_r', 'lon_r'])['road'].transform('nunique') > 1

    # Mark as intersection if it belongs to multiple roads and is not a bridge
    intersection_mask = mask & (one_per_road['model_type'] != 'bridge')

    # Get the rounded coordinates of the intersections
    intersection_points = one_per_road.loc[intersection_mask, ['lat_r', 'lon_r']].drop_duplicates()

    # Merge back to the full network to mark intersections
    network = network.merge(
        intersection_points.assign(is_intersection=True),
        on=['lat_r', 'lon_r'],
        how='left'
    )

    # Fill NaN values in 'is_intersection' with False (non-intersections)
    network['is_intersection'] = network['is_intersection'].fillna(False)

    # Update model_type to 'intersection' for those marked as intersections (but not bridges)
    network.loc[network['is_intersection'] & (network['model_type'] != 'bridge'), 'model_type'] = 'intersection'

    # For rows marked as intersections, assign the same id to all entries with the same rounded coordinates
    network.loc[network['is_intersection'], "id"] = (network.loc[network['is_intersection']].groupby(['lat_r', 'lon_r'])['id'].transform('min'))

    # Drop the temporary rounded coordinate columns and the is_intersection column
    network = network.drop(columns=['lat_r', 'lon_r', 'is_intersection'])

    return network


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

# 2. Round coordinates to detect approximate intersections
roads["lat_round"] = roads["lat"].round(2)
roads["lon_round"] = roads["lon"].round(2)

# 3. Get rounded coordinate points of N1 and N2
n1n2_points = roads[roads["road"].isin(["N1", "N2"])][["lat_round", "lon_round"]].drop_duplicates()

# 4. Find roads that share rounded coordinates with N1 or N2
connected_roads = roads.merge(
    n1n2_points,
    on=["lat_round", "lon_round"],
    how="inner"
)["road"].unique().tolist()

# 5. Keep only long N-roads that are connected
roads_to_use = [r for r in long_roads if r in connected_roads]

# 6. Always include N1 and N2
roads_to_use = sorted(list(set(roads_to_use + ["N1", "N2"])))

print("Roads included in network:", roads_to_use)

# 7. Run pipeline for selected roads
all_networks = []

for road in roads_to_use:
    full_network = process_road_network(
        data_path / "raw" / "BMMS_overview.xlsx",
        data_path / "raw" / "_roads3.csv",
        road
    )
    all_networks.append(full_network)

# 8. Combine all roads
full_network = pd.concat(all_networks, ignore_index=True)

# 9. Assign unique ids
full_network["id"] = range(1_000_000, 1_000_000 + len(full_network))

# Assign intersections
full_network = assign_intersections(full_network)

# 10. Keep only required columns
full_network = full_network[
    ["road", "id", "model_type", "condition", "name", "lat", "lon", "length"]
]

# 11. Save csv (same name as before)
full_network.to_csv(data_path / "processed" / "network_AS3.csv", index=False)

print("Network saved to data/processed/network_AS3.csv")