"""Permanent independent operator checks on the published problem instance."""

from copy import deepcopy
import random
import unittest
from unittest.mock import patch

import problem
from chromosome import generate_random_chromosome, validate_chromosome
from operators import (
    identify_elite,
    mutate_processor,
    tournament_selection,
    whole_portion_crossover,
)
from scheduler import schedule


FIGURE_5 = (
    ("P4", "P1", "P1", "P3", "P4", "P1", "P4", "P2", "P4", "P2"),
    ("t1", "t3", "t5", "t7", "t2", "t4", "t6", "t9", "t8", "t10"),
)
ALL_P1 = (("P1",) * 10, problem.TASK_IDS)
ALL_P2 = (("P2",) * 10, problem.TASK_IDS)

# Two valid allocations on the same published data have makespan 35 but
# different costs and utilisation. They expose any unintended secondary rule.
TIE_LOWER_COST = (
    ("P2", "P2", "P2", "P2", "P1", "P2", "P2", "P2", "P2", "P2"),
    problem.TASK_IDS,
)
TIE_HIGHER_COST = (
    ("P2", "P2", "P2", "P2", "P2", "P2", "P3", "P2", "P2", "P2"),
    problem.TASK_IDS,
)


class OperatorTests(unittest.TestCase):
    def setUp(self):
        self.population = (FIGURE_5, ALL_P1, ALL_P2)
        self.fitness = tuple(schedule(chromosome)["metrics"]["makespan"]
                             for chromosome in self.population)
        self.original_population = deepcopy(self.population)
        self.original_fitness = deepcopy(self.fitness)
        self.original_data = deepcopy((
            problem.TASK_IDS, problem.PROCESSOR_IDS, problem.COMPUTATION_DURATIONS,
            problem.PROCESSOR_RATES, problem.COMMUNICATION_EDGES,
        ))
        self.global_rng_state = random.getstate()

    def tearDown(self):
        self.assertEqual(self.population, self.original_population)
        self.assertEqual(self.fitness, self.original_fitness)
        self.assertEqual((
            problem.TASK_IDS, problem.PROCESSOR_IDS, problem.COMPUTATION_DURATIONS,
            problem.PROCESSOR_RATES, problem.COMMUNICATION_EDGES,
        ), self.original_data)
        self.assertEqual(random.getstate(), self.global_rng_state)

    def test_tournament_lower_makespan_and_three_distinct_indices(self):
        rng = random.Random(42)
        drawn = []
        real_sample = rng.sample

        def record_sample(indices, count):
            result = real_sample(indices, count)
            drawn.extend(result)
            return result

        # Instrument the real RNG only; no problem values or schedules are mocked.
        with patch.object(rng, "sample", side_effect=record_sample) as sampling:
            winner = tournament_selection(self.population, self.fitness, rng)
        sampling.assert_called_once_with(range(3), 3)
        self.assertEqual(len(drawn), 3)
        self.assertEqual(len(set(drawn)), 3)
        self.assertEqual(self.fitness, (46, 32, 22))
        self.assertIs(winner, ALL_P2)

    def test_tournament_ties_use_draw_order_without_secondary_metrics(self):
        low_metrics = schedule(TIE_LOWER_COST)["metrics"]
        high_metrics = schedule(TIE_HIGHER_COST)["metrics"]
        self.assertEqual(low_metrics["makespan"], 35)
        self.assertEqual(high_metrics["makespan"], 35)
        self.assertLess(low_metrics["execution_cost"], high_metrics["execution_cost"])
        self.assertLess(low_metrics["mean_processor_utilisation_pct"],
                        high_metrics["mean_processor_utilisation_pct"])
        for population in (
            (TIE_LOWER_COST, TIE_HIGHER_COST, FIGURE_5),
            (TIE_HIGHER_COST, TIE_LOWER_COST, FIGURE_5),
        ):
            with self.subTest(population=population):
                before = deepcopy(population)
                fitness = (low_metrics["makespan"], high_metrics["makespan"], 46)
                draws = random.Random(0).sample(range(3), 3)
                first_tied_index = next(index for index in draws if fitness[index] == 35)
                self.assertNotEqual(first_tied_index, 0)
                winner = tournament_selection(population, fitness, random.Random(0))
                self.assertIs(winner, population[first_tied_index])
                self.assertEqual(population, before)

    def test_tournament_seeded_replay(self):
        first_rng, second_rng = random.Random(42), random.Random(42)
        self.assertEqual(tournament_selection(self.population, self.fitness, first_rng),
                         tournament_selection(self.population, self.fitness, second_rng))
        self.assertEqual(first_rng.getstate(), second_rng.getstate())

    def test_separate_tournaments_may_return_the_same_parent(self):
        rng = random.Random(42)
        first = tournament_selection(self.population, self.fitness, rng)
        second = tournament_selection(self.population, self.fitness, rng)
        self.assertIs(first, ALL_P2)
        self.assertIs(second, first)

    def test_crossover_probability_one_inherits_whole_portions(self):
        rng = random.Random(42)
        before = deepcopy((ALL_P2, FIGURE_5))
        for _ in range(10):
            child = whole_portion_crossover(ALL_P2, FIGURE_5, 1.0, rng)
            self.assertEqual(child, (ALL_P2[0], FIGURE_5[1]))
            self.assertIsInstance(child, tuple)
            self.assertTrue(all(isinstance(portion, tuple) for portion in child))
            self.assertIs(validate_chromosome(child), True)
        self.assertEqual((ALL_P2, FIGURE_5), before)

    def test_crossover_probability_zero_copies_first_parent(self):
        rng = random.Random(42)
        before = deepcopy((ALL_P2, FIGURE_5))
        for _ in range(10):
            self.assertEqual(whole_portion_crossover(ALL_P2, FIGURE_5, 0.0, rng), ALL_P2)
        self.assertEqual((ALL_P2, FIGURE_5), before)

    def test_crossover_reference_probability_and_rng_replay(self):
        first_rng, second_rng = random.Random(42), random.Random(42)
        first = whole_portion_crossover(ALL_P2, FIGURE_5, 0.95, first_rng)
        second = whole_portion_crossover(ALL_P2, FIGURE_5, 0.95, second_rng)
        self.assertEqual(first, second)
        self.assertEqual(first_rng.getstate(), second_rng.getstate())
        expected_rng = random.Random(42)
        crosses = expected_rng.random() < 0.95
        self.assertEqual(first, (ALL_P2[0], FIGURE_5[1] if crosses else ALL_P2[1]))
        self.assertEqual(first_rng.getstate(), expected_rng.getstate())

    def test_mutation_probability_one_changes_exactly_one_position(self):
        rng = random.Random(42)
        before = deepcopy(FIGURE_5)
        for _ in range(10):
            child = mutate_processor(FIGURE_5, 1.0, rng)
            differences = [index for index in range(10) if child[0][index] != FIGURE_5[0][index]]
            self.assertEqual(len(differences), 1)
            position = differences[0]
            self.assertIn(child[0][position], problem.PROCESSOR_IDS)
            self.assertNotEqual(child[0][position], FIGURE_5[0][position])
            self.assertEqual(child[1], FIGURE_5[1])
            self.assertIsInstance(child, tuple)
            self.assertTrue(all(isinstance(portion, tuple) for portion in child))
            self.assertIs(validate_chromosome(child), True)
        self.assertEqual(FIGURE_5, before)

    def test_mutation_probability_zero_changes_nothing(self):
        rng = random.Random(42)
        before = deepcopy(FIGURE_5)
        with patch.object(rng, "randrange", wraps=rng.randrange) as position_draw:
            with patch.object(rng, "choice", wraps=rng.choice) as processor_draw:
                self.assertEqual(mutate_processor(FIGURE_5, 0.0, rng), FIGURE_5)
        position_draw.assert_not_called()
        processor_draw.assert_not_called()
        self.assertEqual(FIGURE_5, before)

    def test_mutation_single_probability_test_and_seeded_replay(self):
        for probability in (0.02, 1.0):
            with self.subTest(probability=probability):
                first_rng, second_rng = random.Random(42), random.Random(42)
                with patch.object(first_rng, "random", wraps=first_rng.random) as gate:
                    with patch.object(first_rng, "randrange", wraps=first_rng.randrange) as position_draw:
                        with patch.object(first_rng, "choice", wraps=first_rng.choice) as processor_draw:
                            first = mutate_processor(FIGURE_5, probability, first_rng)
                second = mutate_processor(FIGURE_5, probability, second_rng)
                gate.assert_called_once_with()
                self.assertEqual(first, second)
                self.assertEqual(first_rng.getstate(), second_rng.getstate())
                if first != FIGURE_5:
                    position_draw.assert_called_once_with(10)
                    processor_draw.assert_called_once()
                    alternatives = processor_draw.call_args.args[0]
                    self.assertEqual(len(alternatives), 3)
                    self.assertEqual(len(set(alternatives)), 3)
                    position = next(index for index in range(10) if first[0][index] != FIGURE_5[0][index])
                    self.assertEqual(set(alternatives), set(problem.PROCESSOR_IDS) - {FIGURE_5[0][position]})
                else:
                    position_draw.assert_not_called()
                    processor_draw.assert_not_called()

    def test_elite_selects_minimum_makespan(self):
        self.assertIs(identify_elite(self.population, self.fitness), ALL_P2)

    def test_elite_ties_keep_first_minimum_even_with_higher_cost(self):
        population = (FIGURE_5, TIE_HIGHER_COST, TIE_LOWER_COST)
        metrics = tuple(schedule(chromosome)["metrics"] for chromosome in population)
        fitness = tuple(values["makespan"] for values in metrics)
        self.assertGreater(metrics[1]["execution_cost"], metrics[2]["execution_cost"])
        self.assertIs(identify_elite(population, fitness), TIE_HIGHER_COST)

    def test_elite_ties_keep_first_minimum_even_with_lower_utilisation(self):
        population = (FIGURE_5, TIE_LOWER_COST, TIE_HIGHER_COST)
        metrics = tuple(schedule(chromosome)["metrics"] for chromosome in population)
        fitness = tuple(values["makespan"] for values in metrics)
        self.assertLess(metrics[1]["mean_processor_utilisation_pct"],
                        metrics[2]["mean_processor_utilisation_pct"])
        self.assertIs(identify_elite(population, fitness), TIE_LOWER_COST)

    def test_invalid_population_and_fitness_inputs_are_rejected(self):
        for operator in (tournament_selection, identify_elite):
            for population, fitness in (
                ((), ()),
                (self.population, (46, 32)),
                (self.population, (46, float("nan"), 22)),
                (self.population, (46, float("inf"), 22)),
                (self.population, (46, -32, 22)),
            ):
                with self.subTest(operator=operator.__name__, fitness=fitness):
                    arguments = (population, fitness)
                    if operator is tournament_selection:
                        arguments += (random.Random(42),)
                    with self.assertRaises(ValueError):
                        operator(*arguments)
        with self.assertRaisesRegex(ValueError, "at least 3"):
            tournament_selection(self.population[:2], self.fitness[:2], random.Random(42))

    def test_invalid_probabilities_are_rejected(self):
        for probability in (-0.01, 1.01, float("nan"), None, True):
            with self.subTest(probability=probability):
                with self.assertRaisesRegex(ValueError, "Probability"):
                    whole_portion_crossover(ALL_P1, FIGURE_5, probability, random.Random(42))
                with self.assertRaisesRegex(ValueError, "Probability"):
                    mutate_processor(FIGURE_5, probability, random.Random(42))

    def test_single_generated_operator_pipeline(self):
        rng = random.Random(42)
        # Four explicit candidates for this one integration check, not a GA initialiser.
        population = (
            generate_random_chromosome(rng),
            generate_random_chromosome(rng),
            generate_random_chromosome(rng),
            generate_random_chromosome(rng),
        )
        fitness = tuple(schedule(chromosome)["metrics"]["makespan"] for chromosome in population)
        before = deepcopy(population)
        parent_a = tournament_selection(population, fitness, rng)
        parent_b = tournament_selection(population, fitness, rng)
        crossed = whole_portion_crossover(parent_a, parent_b, 0.95, rng)
        child = mutate_processor(crossed, 0.02, rng)
        self.assertIs(validate_chromosome(child), True)
        result = schedule(child)
        self.assertEqual(len(result["trace"]), 10)
        self.assertEqual(result["task_assignments"], dict(zip(child[1], child[0])))
        self.assertEqual(population, before)
        print("Single operator-pipeline validation:", result["metrics"])


if __name__ == "__main__":
    unittest.main()
