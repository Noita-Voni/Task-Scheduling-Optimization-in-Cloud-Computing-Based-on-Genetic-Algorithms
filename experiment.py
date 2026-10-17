"""Phase 4.6: thirty frozen GA runs and two permanent research-results CSVs.

Each seed 1–30 is run once. Runtime covers only the complete run_ga call.
Reproducibility replay is checked separately by the permanent experiment tests.
"""

import csv
from pathlib import Path
import platform
from pprint import pprint
import random
from statistics import mean, median, stdev
from time import perf_counter

from ga import DEFAULT_CONFIGURATION, run_ga


SEEDS = tuple(range(1, 31))
FROZEN_CONFIGURATION = {
    "population_size": 20,
    "generations": 100,
    "tournament_size": 3,
    "crossover_probability": 0.95,
    "mutation_probability": 0.02,
    "elitism": 1,
    "fitness": "makespan",
}
EXPECTED_EVALUATIONS = 1920
RUN_FIELDS = (
    "seed", "initial_best_makespan", "final_best_makespan", "improvement",
    "generation_best_first_found", "execution_cost",
    "paper_aggregate_utilisation_pct", "mean_processor_utilisation_pct",
    "evaluation_count", "runtime_seconds", "final_D", "final_O",
)
HISTORY_FIELDS = (
    "seed", "generation", "best_makespan", "mean_makespan",
    "population_size", "evaluation_count",
)
RESULTS_DIRECTORY = Path(__file__).resolve().parent / "results"


def first_best_generation(history, final_best_makespan):
    """Return the earliest generation that reached the final best makespan."""
    for checkpoint in history:
        if checkpoint["best_makespan"] == final_best_makespan:
            return checkpoint["generation"]
    raise ValueError("The final best makespan does not appear in the history.")


def make_run_record(seed, result, runtime_seconds):
    """Extract one run without changing the GA result or choosing other metrics."""
    if result["configuration"] != FROZEN_CONFIGURATION:
        raise ValueError("A run does not use the frozen Phase 4.6 configuration.")
    if result["evaluation_count"] != EXPECTED_EVALUATIONS:
        raise ValueError("Each research run must evaluate exactly 1920 candidates.")
    history = result["history"]
    if len(history) != 101 or [point["generation"] for point in history] != list(range(101)):
        raise ValueError("Each research run must retain generations 0 through 100.")
    for generation, checkpoint in enumerate(history):
        if checkpoint["population_size"] != 20 or checkpoint["evaluation_count"] != 20 + 19 * generation:
            raise ValueError("History violates the frozen population or evaluation accounting.")
    if any(after["best_makespan"] > before["best_makespan"]
           for before, after in zip(history, history[1:])):
        raise ValueError("Best makespan must not increase under the approved elitism.")

    final_best = result["best_makespan"]
    metrics = result["best_schedule"]["metrics"]
    if final_best != metrics["makespan"] or final_best != history[-1]["best_makespan"]:
        raise ValueError("Final best makespan and its scheduler result disagree.")
    for name in ("execution_cost", "paper_aggregate_utilisation_pct", "mean_processor_utilisation_pct"):
        if result[name] != metrics[name]:
            raise ValueError(f"{name} must belong to the makespan-selected final chromosome.")

    initial_best = history[0]["best_makespan"]
    return {
        "seed": seed,
        "initial_best_makespan": initial_best,
        "final_best_makespan": final_best,
        "improvement": initial_best - final_best,
        "generation_best_first_found": first_best_generation(history, final_best),
        "execution_cost": result["execution_cost"],
        "paper_aggregate_utilisation_pct": result["paper_aggregate_utilisation_pct"],
        "mean_processor_utilisation_pct": result["mean_processor_utilisation_pct"],
        "evaluation_count": result["evaluation_count"],
        "runtime_seconds": runtime_seconds,
        # Space-separated IDs preserve the two positional portions unambiguously.
        "final_D": " ".join(result["best_chromosome"][0]),
        "final_O": " ".join(result["best_chromosome"][1]),
    }


def summarize_runs(runs):
    """Descriptive statistics only; sample standard deviation uses n - 1."""
    if tuple(row["seed"] for row in runs) != SEEDS:
        raise ValueError("Results must contain seeds 1 through 30 exactly once, in order.")
    if any(row["evaluation_count"] != EXPECTED_EVALUATIONS for row in runs):
        raise ValueError("All thirty runs must have 1920 candidate evaluations.")
    makespans = [row["final_best_makespan"] for row in runs]
    improvements = [row["improvement"] for row in runs]
    runtimes = [row["runtime_seconds"] for row in runs]
    best = min(runs, key=lambda row: (row["final_best_makespan"], row["seed"]))
    worst = min(runs, key=lambda row: (-row["final_best_makespan"], row["seed"]))
    return {
        "run_count": len(runs),
        "final_makespan": {
            "minimum": min(makespans), "maximum": max(makespans),
            "mean": mean(makespans), "median": median(makespans),
            "sample_standard_deviation": stdev(makespans),
        },
        "improvement": {
            "runs_improved": sum(value > 0 for value in improvements),
            "runs_no_improvement": sum(value == 0 for value in improvements),
            "mean": mean(improvements), "median": median(improvements),
        },
        "reference_counts": {
            "less_than_46": sum(value < 46 for value in makespans),
            "equal_to_46": sum(value == 46 for value in makespans),
            "greater_than_46": sum(value > 46 for value in makespans),
            "at_most_32": sum(value <= 32 for value in makespans),
            "at_most_22": sum(value <= 22 for value in makespans),
        },
        "best_seed": best["seed"],
        "worst_seed": worst["seed"],
        "runtime_seconds": {"mean": mean(runtimes), "median": median(runtimes)},
    }


def run_experiment(output_dir=None):
    """Execute the fixed thirty runs and save their actual results once.

    Existing research CSVs are never overwritten. Use a separate output directory
    for any subsequently authorised rerun. CSV writing and printing are untimed.
    """
    directory = RESULTS_DIRECTORY if output_dir is None else Path(output_dir)
    run_path = directory / "phase_4_6_ga_runs.csv"
    history_path = directory / "phase_4_6_ga_history.csv"
    if run_path.exists() or history_path.exists():
        raise FileExistsError("Phase 4.6 research results already exist; they will not be overwritten.")
    if DEFAULT_CONFIGURATION != FROZEN_CONFIGURATION:
        raise ValueError("The GA defaults differ from the approved frozen configuration.")

    runs = []
    histories = []
    best_seed = None
    best_result = None
    for seed in SEEDS:
        rng = random.Random(seed)
        started = perf_counter()
        result = run_ga(rng, FROZEN_CONFIGURATION)
        runtime_seconds = perf_counter() - started
        record = make_run_record(seed, result, runtime_seconds)
        runs.append(record)
        histories.extend({"seed": seed, **checkpoint} for checkpoint in result["history"])
        if best_result is None or (result["best_makespan"], seed) < (best_result["best_makespan"], best_seed):
            best_seed = seed
            best_result = result

    summary = summarize_runs(runs)
    directory.mkdir(parents=True, exist_ok=True)
    with run_path.open("x", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=RUN_FIELDS)
        writer.writeheader()
        writer.writerows(runs)
    with history_path.open("x", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=HISTORY_FIELDS)
        writer.writeheader()
        writer.writerows(histories)
    return {
        "runs": runs,
        "history": histories,
        "summary": summary,
        "best_result": best_result,
        "files": {"runs": str(run_path), "history": str(history_path)},
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
    }


if __name__ == "__main__":
    experiment = run_experiment()
    print("Phase 4.6: all 30 fixed-seed research runs completed.")
    print("Seed  Initial  Final  Improvement  First-best-generation  Cost  Runtime-seconds")
    for row in experiment["runs"]:
        print(row["seed"], row["initial_best_makespan"], row["final_best_makespan"],
              row["improvement"], row["generation_best_first_found"],
              row["execution_cost"], f"{row['runtime_seconds']:.6f}")
    pprint(experiment["summary"], sort_dicts=False)
    print("Best chromosome:", experiment["best_result"]["best_chromosome"])
    print("Best scheduler metrics:", experiment["best_result"]["best_schedule"]["metrics"])
    print("Research files:", experiment["files"])
    print("Execution environment:", experiment["environment"])
