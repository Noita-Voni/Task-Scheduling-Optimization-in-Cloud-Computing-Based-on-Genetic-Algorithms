"""Permanent complete-GA checks using the unchanged published instance.

Instrumentation calls the real generators, operators and scheduler. All run
records stay in memory; these checks are not research experiments or exports.
"""

from contextlib import ExitStack
from copy import deepcopy
import random
import unittest
from unittest.mock import patch

import ga
import problem
from chromosome import validate_chromosome
from scheduler import schedule


def recorded_run(seed, configuration=None):
    """Observe real calls without replacing problem data or algorithm results."""
    rng = random.Random(seed)
    events = []
    rng_checks = []
    probability_draws = []
    stochastic = {
        "generate_random_chromosome", "tournament_selection",
        "whole_portion_crossover", "mutate_processor",
    }
    names = (*sorted(stochastic), "schedule", "validate_chromosome", "identify_elite")
    originals = {name: getattr(ga, name) for name in names}
    original_random = rng.random

    def observe(name):
        def call(*arguments):
            observed = arguments
            if name in stochastic:
                rng_checks.append(arguments[-1] is rng)
                observed = arguments[:-1]
            if name in ("tournament_selection", "identify_elite"):
                observed = (tuple(observed[0]), tuple(observed[1]))
            answer = originals[name](*arguments)
            events.append((name, observed, answer))
            return answer
        return call

    def draw_probability():
        value = original_random()
        probability_draws.append(value)
        return value

    with ExitStack() as stack:
        for name in names:
            stack.enter_context(patch.object(ga, name, side_effect=observe(name)))
        stack.enter_context(patch.object(rng, "random", side_effect=draw_probability))
        result = ga.run_ga(rng, configuration)
    return result, events, probability_draws, rng.getstate(), rng_checks


class GATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.problem_before = deepcopy((
            problem.TASK_IDS, problem.PROCESSOR_IDS, problem.COMPUTATION_DURATIONS,
            problem.PROCESSOR_RATES, problem.COMMUNICATION_EDGES,
        ))
        cls.global_rng_before = random.getstate()
        cls.configuration_before = deepcopy(ga.DEFAULT_CONFIGURATION)
        cls.first = recorded_run(42)
        cls.replay = recorded_run(42)
        cls.different = recorded_run(43)

    def events(self, name):
        return [(arguments, answer) for event, arguments, answer in self.first[1]
                if event == name]

    def test_standard_configuration_and_exact_evaluation_accounting(self):
        result = self.first[0]
        self.assertEqual(result["configuration"], {
            "population_size": 20, "generations": 100, "tournament_size": 3,
            "crossover_probability": 0.95, "mutation_probability": 0.02,
            "elitism": 1, "fitness": "makespan",
        })
        self.assertEqual(len(self.events("generate_random_chromosome")), 20)
        self.assertEqual(len(result["initial_population"]), 20)
        self.assertEqual(len(result["final_population"]), 20)
        self.assertEqual(len(self.events("schedule")), 1920)
        self.assertEqual(result["evaluation_count"], 1920)
        self.assertEqual(len(self.events("whole_portion_crossover")), 1900)
        self.assertEqual(len(self.events("mutate_processor")), 1900)
        self.assertEqual(len(self.events("tournament_selection")), 3800)

    def test_every_population_valid_and_every_fitness_is_scheduled_makespan(self):
        evaluations = self.events("schedule")
        evaluated_makespans = {}
        for (chromosome,), evaluated in evaluations:
            self.assertIs(validate_chromosome(chromosome), True)
            self.assertEqual(len(evaluated["trace"]), 10)
            self.assertEqual(evaluated["task_assignments"],
                             dict(zip(chromosome[1], chromosome[0])))
            evaluated_makespans[chromosome] = evaluated["metrics"]["makespan"]
        for arguments, _ in self.events("identify_elite") + self.events("tournament_selection"):
            population, fitness = arguments
            self.assertEqual(len(population), 20)
            self.assertEqual(fitness, tuple(evaluated_makespans[item] for item in population))
            for chromosome in population:
                self.assertIs(validate_chromosome(chromosome), True)
        result = self.first[0]
        for stage in ("initial", "final"):
            self.assertEqual(result[f"{stage}_fitness"], tuple(
                evaluated_makespans[item] for item in result[f"{stage}_population"]
            ))

    def test_replacement_keeps_one_unchanged_elite_and_19_evaluated_children(self):
        elite_calls = self.events("identify_elite")
        evaluations = self.events("schedule")
        self.assertEqual(len(elite_calls), 101)
        self.assertEqual(elite_calls[0][0][0], self.first[0]["initial_population"])
        self.assertEqual(elite_calls[-1][0][0], self.first[0]["final_population"])
        for generation in range(100):
            (population, fitness), elite = elite_calls[generation]
            first_minimum = fitness.index(min(fitness))
            self.assertEqual(elite, population[first_minimum])
            next_population, next_fitness = elite_calls[generation + 1][0]
            self.assertEqual(next_population[0], elite)
            self.assertEqual(next_fitness[0], fitness[first_minimum])
            offset = 20 + generation * 19
            children = evaluations[offset:offset + 19]
            self.assertEqual(next_population[1:], tuple(args[0] for args, _ in children))
            self.assertEqual(next_fitness[1:], tuple(
                item["metrics"]["makespan"] for _, item in children
            ))

    def test_history_means_and_nonincreasing_best_for_all_101_generations(self):
        history = self.first[0]["history"]
        populations = self.events("identify_elite")
        self.assertEqual(len(history), 101)
        self.assertEqual([point["generation"] for point in history], list(range(101)))
        for generation, (point, ((population, fitness), _)) in enumerate(zip(history, populations)):
            self.assertEqual(point["best_makespan"], min(fitness))
            self.assertEqual(point["mean_makespan"], sum(fitness) / len(population))
            self.assertEqual(point["population_size"], 20)
            self.assertEqual(point["evaluation_count"], 20 + 19 * generation)
        for before, after in zip(history, history[1:]):
            self.assertLessEqual(after["best_makespan"], before["best_makespan"])

    def test_each_child_uses_two_tournaments_then_crossover_mutation_validation_schedule(self):
        events = self.first[1]
        first_elite = next(index for index, event in enumerate(events) if event[0] == "identify_elite")
        offspring_events = [event for event in events[first_elite:] if event[0] != "identify_elite"]
        expected_names = ["tournament_selection", "tournament_selection", "whole_portion_crossover",
                          "mutate_processor", "validate_chromosome", "schedule"]
        self.assertEqual(len(offspring_events), 1900 * len(expected_names))
        for offset in range(0, len(offspring_events), len(expected_names)):
            block = offspring_events[offset:offset + len(expected_names)]
            self.assertEqual([event[0] for event in block], expected_names)
            self.assertEqual(block[2][1], (block[0][2], block[1][2], 0.95))
            self.assertEqual(block[3][1], (block[2][2], 0.02))
            self.assertEqual(block[4][1], (block[3][2],))
            self.assertEqual(block[5][1], (block[3][2],))
        self.assertTrue(self.first[4])
        self.assertTrue(all(self.first[4]))
        self.assertEqual(len(self.first[2]), 3800)

    def test_final_first_minimum_and_metrics_reuse_its_original_schedule(self):
        result = self.first[0]
        evaluations = self.events("schedule")
        elite_calls = self.events("identify_elite")
        schedules = [item for _, item in evaluations[:20]]
        for generation in range(100):
            _, fitness = elite_calls[generation][0]
            elite_schedule = schedules[fitness.index(min(fitness))]
            offset = 20 + generation * 19
            schedules = [elite_schedule] + [item for _, item in evaluations[offset:offset + 19]]
        winner_index = result["final_fitness"].index(min(result["final_fitness"]))
        self.assertEqual(result["best_chromosome"], result["final_population"][winner_index])
        self.assertIs(result["best_schedule"], schedules[winner_index])
        # This independent verification is outside run_ga and its evaluation count.
        self.assertEqual(result["best_schedule"], schedule(result["best_chromosome"]))
        metrics = result["best_schedule"]["metrics"]
        self.assertEqual(result["best_makespan"], metrics["makespan"])
        for name in ("execution_cost", "paper_aggregate_utilisation_pct", "mean_processor_utilisation_pct"):
            self.assertEqual(result[name], metrics[name])
        print("Phase 4.5 seed 42 validation:", {
            "initial_best_makespan": result["history"][0]["best_makespan"],
            "final_best_chromosome": result["best_chromosome"],
            "final_metrics": metrics,
            "evaluation_count": result["evaluation_count"],
        })

    def test_same_seed_replays_initial_population_decisions_result_history_and_rng(self):
        self.assertEqual(self.first, self.replay)

    def test_different_seeds_can_produce_different_runs(self):
        self.assertNotEqual(self.first[0]["initial_population"], self.different[0]["initial_population"])
        self.assertNotEqual(self.first[1], self.different[1])

    def test_duplicate_offspring_are_evaluated_when_operator_probabilities_are_zero(self):
        configuration = {"population_size": 3, "generations": 2,
                         "crossover_probability": 0.0, "mutation_probability": 0.0}
        original = deepcopy(configuration)
        result, events, _, _, _ = recorded_run(42, configuration)
        evaluations = [(args[0], answer) for name, args, answer in events if name == "schedule"]
        initial = result["initial_population"]
        winner = initial[result["initial_fitness"].index(min(result["initial_fitness"]))]
        self.assertEqual(len(evaluations), 7)
        self.assertEqual(result["evaluation_count"], 7)
        self.assertEqual([chromosome for chromosome, _ in evaluations[3:]], [winner] * 4)
        self.assertEqual(len({id(answer) for _, answer in evaluations}), 7)
        self.assertEqual(configuration, original)

    def test_zero_replacement_generations_only_initialises_and_evaluates_population(self):
        result, events, _, _, _ = recorded_run(42, {"generations": 0})
        self.assertEqual(result["evaluation_count"], 20)
        self.assertEqual(len(result["history"]), 1)
        self.assertEqual(result["initial_population"], result["final_population"])
        self.assertFalse(any(name == "tournament_selection" for name, _, _ in events))

    def test_invalid_configuration_rejected_before_rng_or_evaluation(self):
        invalid = (
            {"population_size": 2}, {"population_size": True}, {"population_size": 20.5},
            {"generations": -1}, {"generations": True}, {"generations": 1.5},
            {"tournament_size": 4}, {"elitism": 2}, {"fitness": "execution_cost"},
            {"crossover_probability": -0.01}, {"mutation_probability": 1.01},
            {"mutation_probability": float("nan")}, {"mutation_probability": True},
            {"early_stopping": True},
        )
        for configuration in invalid:
            with self.subTest(configuration=configuration):
                rng = random.Random(42)
                state = rng.getstate()
                with patch.object(ga, "schedule", wraps=ga.schedule) as scheduling:
                    with self.assertRaises(ValueError):
                        ga.run_ga(rng, configuration)
                scheduling.assert_not_called()
                self.assertEqual(rng.getstate(), state)

    def test_published_data_default_configuration_and_global_rng_unchanged(self):
        self.assertEqual((
            problem.TASK_IDS, problem.PROCESSOR_IDS, problem.COMPUTATION_DURATIONS,
            problem.PROCESSOR_RATES, problem.COMMUNICATION_EDGES,
        ), self.problem_before)
        self.assertEqual(ga.DEFAULT_CONFIGURATION, self.configuration_before)
        self.assertEqual(random.getstate(), self.global_rng_before)


if __name__ == "__main__":
    unittest.main()
