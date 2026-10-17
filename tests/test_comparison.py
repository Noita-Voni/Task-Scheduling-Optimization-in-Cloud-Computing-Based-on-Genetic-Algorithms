"""Permanent checks of the real Phase 4.7 baseline and paired research files."""

import csv
from math import sqrt
import random
import unittest
from unittest.mock import patch

import baseline
import comparison
import ga
from chromosome import validate_chromosome
from experiment import RESULTS_DIRECTORY, SEEDS
from scheduler import schedule


class ComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = (
            RESULTS_DIRECTORY / "phase_4_7_random_runs.csv",
            RESULTS_DIRECTORY / "phase_4_7_random_history.csv",
            RESULTS_DIRECTORY / "phase_4_7_comparison.csv",
        )
        cls.ga_path = RESULTS_DIRECTORY / "phase_4_6_ga_runs.csv"
        cls.tables = []
        for path in (*cls.paths, cls.ga_path):
            with path.open(newline="", encoding="utf-8") as source:
                reader = csv.DictReader(source)
                cls.tables.append((tuple(reader.fieldnames), list(reader)))
        cls.random_rows = cls.tables[0][1]
        cls.history = cls.tables[1][1]
        cls.pairs = cls.tables[2][1]
        cls.ga_rows = cls.tables[3][1]
        cls.by_seed = {seed: [point for point in cls.history if int(point["seed"]) == seed]
                       for seed in SEEDS}

    def test_research_files_cover_all_seeds_and_exact_equal_budgets(self):
        self.assertEqual(self.tables[0][0], comparison.RANDOM_FIELDS)
        self.assertEqual(self.tables[1][0], comparison.HISTORY_FIELDS)
        self.assertEqual(self.tables[2][0], comparison.COMPARISON_FIELDS)
        self.assertEqual([int(row["seed"]) for row in self.random_rows], list(SEEDS))
        self.assertEqual(len(self.history), 30 * 1920)
        for row in self.random_rows:
            seed = int(row["seed"])
            with self.subTest(seed=seed):
                self.assertEqual(int(row["evaluation_count"]), 1920)
                self.assertGreater(float(row["runtime_seconds"]), 0)
                points = self.by_seed[seed]
                self.assertEqual(len(points), 1920)
                self.assertEqual([int(point["evaluation_count"]) for point in points], list(range(1, 1921)))
                running_best = None
                for point in points:
                    value = int(point["candidate_makespan"])
                    running_best = value if running_best is None else min(running_best, value)
                    self.assertEqual(int(point["best_makespan"]), running_best)
                self.assertEqual(int(row["initial_best_makespan"]),
                                 min(int(point["candidate_makespan"]) for point in points[:20]))
                self.assertEqual(int(row["final_best_makespan"]), running_best)
                self.assertEqual(int(row["improvement"]),
                                 int(row["initial_best_makespan"]) - running_best)
                self.assertEqual(int(row["evaluation_best_first_found"]),
                                 next(int(point["evaluation_count"]) for point in points
                                      if int(point["candidate_makespan"]) == running_best))

    def test_all_saved_winning_chromosomes_reproduce_published_schedule_metrics(self):
        for row in self.random_rows:
            with self.subTest(seed=row["seed"]):
                chromosome = (tuple(row["final_D"].split()), tuple(row["final_O"].split()))
                self.assertIs(validate_chromosome(chromosome), True)
                metrics = schedule(chromosome)["metrics"]
                for field, metric in (("final_best_makespan", "makespan"),
                                      ("execution_cost", "execution_cost")):
                    self.assertEqual(int(row[field]), metrics[metric])
                for field in ("paper_aggregate_utilisation_pct", "mean_processor_utilisation_pct"):
                    self.assertEqual(float(row[field]), metrics[field])

    def test_paired_initial_samples_and_saved_ga_rows(self):
        self.assertEqual([int(row["seed"]) for row in self.ga_rows], list(SEEDS))
        for random_row, ga_row in zip(self.random_rows, self.ga_rows):
            self.assertEqual(random_row["seed"], ga_row["seed"])
            self.assertEqual(random_row["initial_best_makespan"], ga_row["initial_best_makespan"])
            self.assertEqual(int(ga_row["evaluation_count"]), 1920)
        ga_replay = ga.run_ga(random.Random(1))
        baseline_replay = baseline.run_random_search(random.Random(1))
        self.assertEqual(baseline_replay["initial_population"], ga_replay["initial_population"])
        self.assertEqual(baseline_replay["initial_fitness"], ga_replay["initial_fitness"])

    def test_actual_generator_validity_first_minimum_and_seed_one_replay(self):
        original_files = tuple(path.read_bytes() for path in (*self.paths, self.ga_path))
        real_generate = baseline.generate_random_chromosome
        generated = []

        def checked_generate(rng):
            chromosome = real_generate(rng)
            self.assertIs(validate_chromosome(chromosome), True)
            generated.append(chromosome)
            return chromosome

        with patch.object(baseline, "generate_random_chromosome", side_effect=checked_generate):
            replay = baseline.run_random_search(random.Random(1))
        self.assertEqual(len(generated), 1920)
        saved = self.random_rows[0]
        self.assertEqual(replay["best_chromosome"],
                         (tuple(saved["final_D"].split()), tuple(saved["final_O"].split())))
        self.assertEqual(replay["best_makespan"], int(saved["final_best_makespan"]))
        self.assertEqual(replay["evaluation_count"], int(saved["evaluation_count"]))
        self.assertEqual(replay["best_first_evaluation"], int(saved["evaluation_best_first_found"]))
        for field in ("execution_cost", "paper_aggregate_utilisation_pct", "mean_processor_utilisation_pct"):
            self.assertEqual(replay[field], float(saved[field]))
        self.assertEqual(replay["history"],
                         [{name: int(point[name]) for name in ("evaluation_count", "candidate_makespan", "best_makespan")}
                          for point in self.by_seed[1]])
        self.assertEqual(replay["best_chromosome"], generated[replay["best_first_evaluation"] - 1])
        self.assertEqual(replay["best_schedule"], schedule(replay["best_chromosome"]))
        self.assertEqual(original_files, tuple(path.read_bytes() for path in (*self.paths, self.ga_path)))
        print("Phase 4.7 reproducibility replay: PASS, seed 1; research CSVs unchanged.")

    def test_paired_differences_summary_and_descriptive_reference_counts(self):
        computed_pairs, paired = comparison.compare_paired_runs(self.ga_rows, self.random_rows)
        self.assertEqual(self.pairs, [{name: str(row[name]) for name in comparison.COMPARISON_FIELDS}
                                      for row in computed_pairs])
        differences = [int(row["ga_minus_random"]) for row in self.pairs]
        self.assertEqual(paired["ga_wins"], sum(value < 0 for value in differences))
        self.assertEqual(paired["ties"], sum(value == 0 for value in differences))
        self.assertEqual(paired["random_wins"], sum(value > 0 for value in differences))
        self.assertEqual(paired["mean_paired_difference"], sum(differences) / 30)
        ordered_differences = sorted(differences)
        self.assertEqual(paired["median_paired_difference"],
                         (ordered_differences[14] + ordered_differences[15]) / 2)

        rows = []
        for raw in self.random_rows:
            row = raw.copy()
            for name in ("seed", "initial_best_makespan", "final_best_makespan", "improvement",
                         "evaluation_count"):
                row[name] = int(row[name])
            row["runtime_seconds"] = float(row["runtime_seconds"])
            rows.append(row)
        from experiment import summarize_runs
        summary = summarize_runs(rows)
        values = [row["final_best_makespan"] for row in rows]
        average = sum(values) / 30
        self.assertEqual(summary["final_makespan"]["minimum"], min(values))
        self.assertEqual(summary["final_makespan"]["maximum"], max(values))
        self.assertEqual(summary["final_makespan"]["mean"], average)
        self.assertEqual(summary["final_makespan"]["median"],
                         (sorted(values)[14] + sorted(values)[15]) / 2)
        self.assertAlmostEqual(summary["final_makespan"]["sample_standard_deviation"],
                               sqrt(sum((value - average) ** 2 for value in values) / 29))
        for threshold_name, count in {
            "less_than_46": sum(value < 46 for value in values),
            "equal_to_46": sum(value == 46 for value in values),
            "greater_than_46": sum(value > 46 for value in values),
            "at_most_32": sum(value <= 32 for value in values),
            "at_most_22": sum(value <= 22 for value in values),
        }.items():
            self.assertEqual(summary["reference_counts"][threshold_name], count)

    def test_saved_results_are_protected_before_any_new_baseline_run(self):
        original_files = tuple(path.read_bytes() for path in (*self.paths, self.ga_path))
        with patch.object(comparison, "run_random_search", wraps=comparison.run_random_search) as running:
            with self.assertRaises(FileExistsError):
                comparison.run_comparison()
        running.assert_not_called()
        self.assertEqual(original_files, tuple(path.read_bytes() for path in (*self.paths, self.ga_path)))
        mismatched_ga = self.ga_rows[1:] + self.ga_rows[:1]
        with self.assertRaises(ValueError):
            comparison.compare_paired_runs(mismatched_ga, self.random_rows)


if __name__ == "__main__":
    unittest.main()
