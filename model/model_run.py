import os
import pandas as pd
from model import BangladeshModel
from components import Source, Bridge

SINGLE_RUN = False # Set to False to run the scenario experiment
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'experiment')

# ---------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------
SCENARIOS = [0, 1, 2, 3, 4]
SCENARIOS = [2] if SINGLE_RUN else SCENARIOS
RUNS = 1 if SINGLE_RUN else 10
TICKS = 7200         # 5 days * 24 hours * 60 minutes
SEED_BASE = 1234567
BREAKDOWN_RATES = {
    0: {'A': 0.00, 'B': 0.00, 'C': 0.00, 'D': 0.00},
    1: {'A': 0.00, 'B': 0.00, 'C': 0.00, 'D': 0.05},
    2: {'A': 0.00, 'B': 0.00, 'C': 0.05, 'D': 0.10},
    3: {'A': 0.00, 'B': 0.05, 'C': 0.10, 'D': 0.20},
    4: {'A': 0.05, 'B': 0.10, 'C': 0.20, 'D': 0.40},
}

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ---------------------------------------------------------------
def run_scenario(scenario, run, seed):
    """
    Run a single simulation and return a DataFrame of vehicle travel times.
    """
    print(f"  Running scenario {scenario}, run {run}, seed {seed}...")

    # Reset truck counter between runs
    Source.truck_counter = 0
    scenario_breakdown_rates = BREAKDOWN_RATES[scenario]
    model = BangladeshModel(seed=seed, scenario=scenario_breakdown_rates)

    for tick in range(TICKS):
        model.step()

    print(f"    -> travel_times collected: {len(model.travel_times)}")

    # Add completion_rate to the records
    generated_trucks = Source.truck_counter
    completed_trucks = len(model.travel_times)
    completion_rate = completed_trucks / generated_trucks if generated_trucks > 0 else 0

    # Collect travel times recorded during the run via model.travel_times
    records = []
    for record in model.travel_times:
        records.append({
            'vehicle_id': record['vehicle_id'],
            'generated_at_step': record['generated_at_step'],
            'removed_at_step': record['removed_at_step'],
            'travel_time_min': record['travel_time_min'],
            'total_delay_time_min': record['total_delay_time_min'],
            'generated_by': record['generated_by'],
            'scenario': scenario,
            'run': run
        })

    df_run = pd.DataFrame(records)

    p95_travel_time = df_run['travel_time_min'].quantile(0.95) if not df_run.empty else None

    bridges = [agent for agent in model.schedule.agents if isinstance(agent, Bridge)]
    broken_by_condition = {'A': 0, 'B': 0, 'C': 0, 'D': 0}

    for bridge in bridges:
        cond = str(bridge.condition).strip().upper()

        if cond in broken_by_condition and bridge.broken:
            broken_by_condition[cond] += 1

    mean_delay_per_truck = df_run['total_delay_time_min'].mean() if not df_run.empty else None

    run_metrics = {
        'scenario': scenario,
        'run': run,
        'seed': seed,
        'generated_trucks': generated_trucks,
        'completed_trucks': completed_trucks,
        'completion_rate': completion_rate,
        'p95_travel_time': p95_travel_time,
        'broken_bridges_count': sum(broken_by_condition.values()),
        'broken_A': broken_by_condition['A'],
        'broken_B': broken_by_condition['B'],
        'broken_C': broken_by_condition['C'],
        'broken_D': broken_by_condition['D'],
        'mean_delay_per_truck': mean_delay_per_truck
    }

    print(f"    -> {len(records)} vehicles completed in scenario {scenario} run {run}")
    return df_run, run_metrics


# ---------------------------------------------------------------
def main():
    all_results = []
    all_run_metrics = []

    for scenario in SCENARIOS:
        scenario_results = []

        for run in range(RUNS):
            # seed = SEED_BASE + scenario * 100 + run
            seed = SEED_BASE + run
            df_run, metrics_run = run_scenario(scenario, run, seed)
            scenario_results.append(df_run)
            all_run_metrics.append(metrics_run)

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

    # Save run metrics
    df_run_metrics = pd.DataFrame(all_run_metrics)
    df_run_metrics.to_csv(os.path.join(OUTPUT_DIR, 'run_metrics.csv'), index=False)


# ---------------------------------------------------------------
if __name__ == '__main__':
    main()