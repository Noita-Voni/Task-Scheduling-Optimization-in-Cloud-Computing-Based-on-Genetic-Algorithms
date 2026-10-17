"""Phase 4.6 checks using the permanently retained real research outputs.

Run experiment.py once before these tests if the research CSVs are not present.
Tests read those outputs and replay seed 1; they never replace the saved runs.
"""

import csv
from math import sqrt
import random
import unittest
from unittest.mock import patch

import experiment
import ga
from chromosome import validate_chromosome
from scheduler import schedule


class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.run_path = experiment.RESULTS_DIRECTORY / "phase_4_6_ga_runs.csv"
        cls.history_path = experiment.RESULTS_DIRECTORY / "phase_4_6_ga_history.csv"
        with cls.run_path.open(newline="", encoding="utf-8") as source:
            reader = csv.DictReader(source)
            cls.run_fields = tuple(reader.fieldnames)
            cls.runs = list(reader)
        integer_fields = (
            "seed", "initial_best_makespan", "final_best_makespan", "improvement",
            "generation_best_first_found", "execution_cost", "evaluation_count",
        )
        for row in cls.runs:
            for name in integer_fields:
                row[name] = int(row[name])
            for name in ("paper_aggregate_utilisation_pct", "mean_processor_utilisation_pct", "runtime_seconds"):
                row[name] = float(row[name])
        with cls.history_path.open(newline="", encoding="utf-8") as source:
            reader = csv.DictReader(source)
            cls.history_fields = tuple(reader.fieldnames)
            cls.history = list(reader)
        for point in cls.history:
            for name in ("seed", "generation", "best_makespan", "population_size", "evaluation_count"):
                point[name] = int(point[name])
            point["mean_makespan"] = float(point["mean_makespan"])
        cls.by_seed = {seed: [point for point in cls.history if point["seed"] == seed]
                       for seed in experiment.SEEDS}

    def test_exact_thirty_seeds_and_frozen_evaluation_counts(self):
        self.assertEqual(experiment.SEEDS, tuple(range(1, 31)))
        self.assertEqual(len(self.runs), 30)
        self.assertEqual(tuple(row["seed"] for row in self.runs), experiment.SEEDS)
        self.assertEqual(experiment.FROZEN_CONFIGURATION, ga.DEFAULT_CONFIGURATION)
        self.assertTrue(all(row["evaluation_count"] == 1920 for row in self.runs))
        self.assertTrue(all(row["runtime_seconds"] > 0 for row in self.runs))

    def test_all_3030_history_checkpoints_preserve_generation_and_budget(self):
        self.assertEqual(len(self.history), 3030)
        for seed, history in self.by_seed.items():
            with self.subTest(seed=seed):
                self.assertEqual(len(history), 101)
                self.assertEqual([point["generation"] for point in history], list(range(101)))
                for generation, point in enumerate(history):
                    self.assertEqual(point["population_size"], 20)
                    self.assertEqual(point["evaluation_count"], 20 + 19 * generation)
                    self.assertGreaterEqual(point["mean_makespan"], point["best_makespan"])
                for before, after in zip(history, history[1:]):
                    self.assertLessEqual(after["best_makespan"], before["best_makespan"])

    def test_each_saved_final_chromosome_reproduces_its_metrics(self):
        for row in self.runs:
            with self.subTest(seed=row["seed"]):
                chromosome = (tuple(row["final_D"].split()), tuple(row["final_O"].split()))
                self.assertIs(validate_chromosome(chromosome), True)
                metrics = schedule(chromosome)["metrics"]
                self.assertEqual(row["final_best_makespan"], metrics["makespan"])
                self.assertEqual(row["execution_cost"], metrics["execution_cost"])
                for name in ("paper_aggregate_utilisation_pct", "mean_processor_utilisation_pct"):
                    self.assertEqual(row[name], metrics[name])

    def test_improvement_and_earliest_best_generation_match_saved_histories(self):
        for row in self.runs:
            with self.subTest(seed=row["seed"]):
                history = self.by_seed[row["seed"]]
                self.assertEqual(row["initial_best_makespan"], history[0]["best_makespan"])
                self.assertEqual(row["final_best_makespan"], history[-1]["best_makespan"])
                self.assertEqual(row["improvement"], row["initial_best_makespan"] - row["final_best_makespan"])
                self.assertGreaterEqual(row["improvement"], 0)
                generation = experiment.first_best_generation(history, row["final_best_makespan"])
                self.assertEqual(row["generation_best_first_found"], generation)
                self.assertEqual(history[generation]["best_makespan"], row["final_best_makespan"])
                self.assertTrue(all(point["best_makespan"] > row["final_best_makespan"]
                                    for point in history[:generation]))

    def test_descriptive_statistics_include_sample_standard_deviation(self):
        summary = experiment.summarize_runs(self.runs)
        values = [row["final_best_makespan"] for row in self.runs]
        ordered = sorted(values)
        average = sum(values) / 30
        sample_sd = sqrt(sum((value - average) ** 2 for value in values) / 29)
        statistics = summary["final_makespan"]
        self.assertEqual(statistics["minimum"], ordered[0])
        self.assertEqual(statistics["maximum"], ordered[-1])
        self.assertEqual(statistics["mean"], average)
        self.assertEqual(statistics["median"], (ordered[14] + ordered[15]) / 2)
        self.assertAlmostEqual(statistics["sample_standard_deviation"], sample_sd)
        improvements = sorted(row["improvement"] for row in self.runs)
        self.assertEqual(summary["improvement"]["runs_improved"], sum(value > 0 for value in improvements))
        self.assertEqual(summary["improvement"]["runs_no_improvement"], sum(value == 0 for value in improvements))
        self.assertEqual(summary["improvement"]["mean"], sum(improvements) / 30)
        self.assertEqual(summary["improvement"]["median"], (improvements[14] + improvements[15]) / 2)
        runtimes = sorted(row["runtime_seconds"] for row in self.runs)
        self.assertAlmostEqual(summary["runtime_seconds"]["mean"], sum(runtimes) / 30)
        self.assertEqual(summary["runtime_seconds"]["median"], (runtimes[14] + runtimes[15]) / 2)

    def test_reference_counts_and_smallest_seed_reporting_ties(self):
        summary = experiment.summarize_runs(self.runs)
        values = [row["final_best_makespan"] for row in self.runs]
        expected = {
            "less_than_46": sum(value < 46 for value in values),
            "equal_to_46": sum(value == 46 for value in values),
            "greater_than_46": sum(value > 46 for value in values),
            "at_most_32": sum(value <= 32 for value in values),
            "at_most_22": sum(value <= 22 for value in values),
        }
        self.assertEqual(summary["reference_counts"], expected)
        self.assertEqual(summary["best_seed"], min(row["seed"] for row in self.runs
                                                  if row["final_best_makespan"] == min(values)))
        self.assertEqual(summary["worst_seed"], min(row["seed"] for row in self.runs
                                                   if row["final_best_makespan"] == max(values)))

    def test_csv_fields_and_saved_results_are_protected_from_overwrite(self):
        self.assertEqual(self.run_fields, experiment.RUN_FIELDS)
        self.assertEqual(self.history_fields, experiment.HISTORY_FIELDS)
        before = (self.run_path.read_bytes(), self.history_path.read_bytes())
        with patch.object(experiment, "run_ga", wraps=experiment.run_ga) as running:
            with self.assertRaises(FileExistsError):
                experiment.run_experiment()
        running.assert_not_called()
        self.assertEqual(before, (self.run_path.read_bytes(), self.history_path.read_bytes()))

    def test_seed_one_replay_matches_saved_research_output_without_overwriting(self):
        before = (self.run_path.read_bytes(), self.history_path.read_bytes())
        original = next(row for row in self.runs if row["seed"] == 1)
        replay = ga.run_ga(random.Random(1), experiment.FROZEN_CONFIGURATION)
        self.assertEqual(replay["best_chromosome"],
                         (tuple(original["final_D"].split()), tuple(original["final_O"].split())))
        self.assertEqual(replay["best_makespan"], original["final_best_makespan"])
        self.assertEqual(replay["evaluation_count"], original["evaluation_count"])
        for name in ("execution_cost", "paper_aggregate_utilisation_pct", "mean_processor_utilisation_pct"):
            self.assertEqual(replay[name], original[name])
        original_history = [{name: point[name] for name in ga_point}
                            for point, ga_point in zip(self.by_seed[1], replay["history"])]
        self.assertEqual(replay["history"], original_history)
        self.assertEqual(replay["best_schedule"], schedule(replay["best_chromosome"]))
        self.assertEqual(before, (self.run_path.read_bytes(), self.history_path.read_bytes()))
        print("Phase 4.6 reproducibility replay: PASS, seed 1; original CSVs unchanged.")


if __name__ == "__main__":
    unittest.main()
