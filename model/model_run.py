import os
import pandas as pd
from model import BangladeshModel
from components import Source

# ---------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------
SCENARIOS = [0]
RUNS = 1
TICKS = 7200         # 5 days * 24 hours * 60 minutes
SEED_BASE = 1234567
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'experiment')

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ---------------------------------------------------------------
def run_scenario(scenario, run, seed):
    """
    Run a single simulation and return a DataFrame of vehicle travel times.
    """
    print(f"  Running scenario {scenario}, run {run}, seed {seed}...")

    # Reset truck counter between runs
    Source.truck_counter = 0

    model = BangladeshModel(seed=seed, scenario=scenario)

    for tick in range(TICKS):
        model.step()

    print(f"    -> travel_times collected: {len(model.travel_times)}")

    # Collect travel times recorded during the run via model.travel_times
    records = []
    for record in model.travel_times:
        records.append({
            'vehicle_id': record['vehicle_id'],
            'generated_at_step': record['generated_at_step'],
            'removed_at_step': record['removed_at_step'],
            'travel_time_min': record['travel_time_min'],
            'generated_by': record['generated_by'],
            'scenario': scenario,
            'run': run
        })

    print(f"    -> {len(records)} vehicles completed in scenario {scenario} run {run}")
    return pd.DataFrame(records)


# ---------------------------------------------------------------
def main():
    all_results = []

    for scenario in SCENARIOS:
        scenario_results = []

        for run in range(RUNS):
            seed = SEED_BASE + scenario * 100 + run
            df_run = run_scenario(scenario, run, seed)
            scenario_results.append(df_run)

        # Save per-scenario CSV
        df_scenario = pd.concat(scenario_results, ignore_index=True)
        out_path = os.path.join(OUTPUT_DIR, f'scenario{scenario}.csv')
        df_scenario.to_csv(out_path, index=False)
        print(f"  Saved {out_path} ({len(df_scenario)} records)")

        all_results.append(df_scenario)

    # Save combined CSV
    df_all = pd.concat(all_results, ignore_index=True)
    df_all.to_csv(os.path.join(OUTPUT_DIR, 'all_scenarios.csv'), index=False)

    # Print and save summary statistics
    print("\n=== SUMMARY ===")
    summary = df_all.groupby('scenario')['travel_time_min'].agg(['mean', 'median', 'std', 'count', 'sum'])
    summary.columns = ['mean_travel_time', 'median_travel_time', 'std_travel_time', 'vehicle_count', 'total_travel_time']
    print(summary.to_string())
    summary.to_csv(os.path.join(OUTPUT_DIR, 'summary.csv'))
    print(f"\nAll results saved to {OUTPUT_DIR}")


# ---------------------------------------------------------------
if __name__ == '__main__':
    main()