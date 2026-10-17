"""Phase 4.7: paired equal-budget random baseline against saved GA results."""

import csv
from pathlib import Path
import random
from statistics import mean, median
from time import perf_counter

from baseline import EVALUATION_BUDGET, INITIAL_SAMPLE_SIZE, run_random_search
from experiment import RESULTS_DIRECTORY, SEEDS, summarize_runs


RANDOM_FIELDS = (
    "seed", "initial_best_makespan", "final_best_makespan", "improvement",
    "evaluation_best_first_found", "execution_cost",
    "paper_aggregate_utilisation_pct", "mean_processor_utilisation_pct",
    "evaluation_count", "runtime_seconds", "final_D", "final_O",
)
HISTORY_FIELDS = ("seed", "evaluation_count", "candidate_makespan", "best_makespan")
COMPARISON_FIELDS = ("seed", "ga_final_makespan", "random_final_makespan", "ga_minus_random")


def load_saved_ga_runs(path):
    """Read the published Phase 4.6 result file without editing or replaying it."""
    with Path(path).open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    if len(rows) != len(SEEDS) or tuple(int(row["seed"]) for row in rows) != SEEDS:
        raise ValueError("Saved GA results must contain seeds 1 through 30 exactly once, in order.")
    if any(int(row["evaluation_count"]) != EVALUATION_BUDGET for row in rows):
        raise ValueError("Every saved GA run must have 1920 evaluations.")
    return rows


def make_baseline_record(seed, result, runtime_seconds):
    """Extract metrics belonging to the first makespan-minimum chromosome."""
    if result["evaluation_count"] != EVALUATION_BUDGET:
        raise ValueError("The baseline must evaluate exactly 1920 candidates.")
    if len(result["initial_population"]) != INITIAL_SAMPLE_SIZE or len(result["history"]) != EVALUATION_BUDGET:
        raise ValueError("Baseline initial sample or history has the wrong length.")
    history = result["history"]
    if any(point["evaluation_count"] != index for index, point in enumerate(history, start=1)):
        raise ValueError("Baseline history must retain every evaluation in order.")
    first_found = next(point["evaluation_count"] for point in history
                       if point["candidate_makespan"] == result["best_makespan"])
    if first_found != result["best_first_evaluation"] or history[-1]["best_makespan"] != result["best_makespan"]:
        raise ValueError("The baseline winner disagrees with its candidate history.")
    metrics = result["best_schedule"]["metrics"]
    if result["best_makespan"] != metrics["makespan"]:
        raise ValueError("The winning makespan and saved schedule disagree.")
    for name in ("execution_cost", "paper_aggregate_utilisation_pct", "mean_processor_utilisation_pct"):
        if result[name] != metrics[name]:
            raise ValueError(f"{name} does not belong to the selected chromosome.")
    return {
        "seed": seed,
        "initial_best_makespan": result["initial_best_makespan"],
        "final_best_makespan": result["best_makespan"],
        "improvement": result["initial_best_makespan"] - result["best_makespan"],
        "evaluation_best_first_found": first_found,
        "execution_cost": result["execution_cost"],
        "paper_aggregate_utilisation_pct": result["paper_aggregate_utilisation_pct"],
        "mean_processor_utilisation_pct": result["mean_processor_utilisation_pct"],
        "evaluation_count": result["evaluation_count"],
        "runtime_seconds": runtime_seconds,
        "final_D": " ".join(result["best_chromosome"][0]),
        "final_O": " ".join(result["best_chromosome"][1]),
    }


def compare_paired_runs(ga_rows, random_rows):
    """Calculate GA minus random makespan for matching saved seed rows."""
    if len(ga_rows) != len(SEEDS) or len(random_rows) != len(SEEDS):
        raise ValueError("Both protocols require all 30 seed results.")
    pairs = []
    for expected_seed, ga_row, random_row in zip(SEEDS, ga_rows, random_rows):
        if int(ga_row["seed"]) != expected_seed or int(random_row["seed"]) != expected_seed:
            raise ValueError("GA and random results must match seeds 1 through 30 in order.")
        ga_makespan = int(ga_row["final_best_makespan"])
        random_makespan = int(random_row["final_best_makespan"])
        pairs.append({
            "seed": expected_seed,
            "ga_final_makespan": ga_makespan,
            "random_final_makespan": random_makespan,
            "ga_minus_random": ga_makespan - random_makespan,
        })
    differences = [row["ga_minus_random"] for row in pairs]
    return pairs, {
        "ga_wins": sum(value < 0 for value in differences),
        "ties": sum(value == 0 for value in differences),
        "random_wins": sum(value > 0 for value in differences),
        "mean_paired_difference": mean(differences),
        "median_paired_difference": median(differences),
    }


def _write_csv(path, fields, rows):
    with path.open("x", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run_comparison(output_dir=RESULTS_DIRECTORY):
    """Run seeds 1-30 once, then compare them with immutable Phase 4.6 rows."""
    directory = Path(output_dir)
    run_path = directory / "phase_4_7_random_runs.csv"
    history_path = directory / "phase_4_7_random_history.csv"
    comparison_path = directory / "phase_4_7_comparison.csv"
    if any(path.exists() for path in (run_path, history_path, comparison_path)):
        raise FileExistsError("Phase 4.7 research results already exist; they will not be overwritten.")
    ga_rows = load_saved_ga_runs(RESULTS_DIRECTORY / "phase_4_6_ga_runs.csv")

    random_rows = []
    history_rows = []
    best_result = None
    best_seed = None
    for seed, ga_row in zip(SEEDS, ga_rows):
        rng = random.Random(seed)
        started = perf_counter()
        result = run_random_search(rng)
        runtime_seconds = perf_counter() - started
        row = make_baseline_record(seed, result, runtime_seconds)
        if row["initial_best_makespan"] != int(ga_row["initial_best_makespan"]):
            raise ValueError(f"Seed {seed} does not share the saved GA initial sample best.")
        random_rows.append(row)
        history_rows.extend({"seed": seed, **point} for point in result["history"])
        if best_result is None or (row["final_best_makespan"], seed) < (best_result["best_makespan"], best_seed):
            best_result = result
            best_seed = seed

    pairs, paired_summary = compare_paired_runs(ga_rows, random_rows)
    random_summary = summarize_runs(random_rows)
    ga_counts = {
        "less_than_46": sum(int(row["final_best_makespan"]) < 46 for row in ga_rows),
        "equal_to_46": sum(int(row["final_best_makespan"]) == 46 for row in ga_rows),
        "greater_than_46": sum(int(row["final_best_makespan"]) > 46 for row in ga_rows),
        "at_most_32": sum(int(row["final_best_makespan"]) <= 32 for row in ga_rows),
        "at_most_22": sum(int(row["final_best_makespan"]) <= 22 for row in ga_rows),
    }
    directory.mkdir(parents=True, exist_ok=True)
    _write_csv(run_path, RANDOM_FIELDS, random_rows)
    _write_csv(history_path, HISTORY_FIELDS, history_rows)
    _write_csv(comparison_path, COMPARISON_FIELDS, pairs)
    return {
        "random_rows": random_rows,
        "history": history_rows,
        "pairs": pairs,
        "paired_summary": paired_summary,
        "random_summary": random_summary,
        "ga_reference_counts": ga_counts,
        "best_result": best_result,
        "files": {"random_runs": str(run_path), "random_history": str(history_path),
                  "comparison": str(comparison_path)},
    }


if __name__ == "__main__":
    result = run_comparison()
    for row in result["random_rows"]:
        print(row["seed"], row["initial_best_makespan"], row["final_best_makespan"],
              row["improvement"], row["evaluation_best_first_found"],
              row["execution_cost"], f"{row['runtime_seconds']:.6f}")
    print("Random summary:", result["random_summary"])
    print("GA reference counts:", result["ga_reference_counts"])
    print("Paired comparison:", result["paired_summary"])
    print("Best random chromosome:", result["best_result"]["best_chromosome"])
    print("Best random scheduler metrics:", result["best_result"]["best_schedule"]["metrics"])
    print("Research files:", result["files"])
