"""Phase 4.3 validity and replay checks on the actual published instance."""

from copy import deepcopy
import random
import unittest

import problem
from chromosome import (
    generate_random_chromosome,
    random_processor_distribution,
    random_topological_order,
    validate_chromosome,
)
from scheduler import schedule


FIGURE_5_D = ("P4", "P1", "P1", "P3", "P4", "P1", "P4", "P2", "P4", "P2")
FIGURE_5_O = ("t1", "t3", "t5", "t7", "t2", "t4", "t6", "t9", "t8", "t10")


class ChromosomeTests(unittest.TestCase):
    def setUp(self):
        self.original_data = deepcopy(self.problem_data())
        self.global_rng_state = random.getstate()

    def tearDown(self):
        self.assertEqual(self.problem_data(), self.original_data)
        self.assertEqual(random.getstate(), self.global_rng_state)

    def problem_data(self):
        return (
            problem.TASK_IDS,
            problem.PROCESSOR_IDS,
            problem.COMPUTATION_DURATIONS,
            problem.PROCESSOR_RATES,
            problem.COMMUNICATION_EDGES,
        )

    def assert_valid_order(self, order):
        self.assertEqual(len(order), 10)
        self.assertEqual(len(set(order)), 10)
        self.assertEqual(set(order), set(problem.TASK_IDS))
        self.assertEqual(order[0], "t1")
        self.assertEqual(order[-1], "t10")
        positions = {task: position for position, task in enumerate(order)}
        for parent, child, _ in problem.COMMUNICATION_EDGES:
            self.assertLess(positions[parent], positions[child])

    def test_figure_5_is_accepted_with_positional_pairing(self):
        chromosome = (FIGURE_5_D, FIGURE_5_O)
        original = deepcopy(chromosome)
        self.assertIs(validate_chromosome(chromosome), True)
        result = schedule(chromosome)
        self.assertEqual(result["task_assignments"], {
            "t1": "P4", "t3": "P1", "t5": "P1", "t7": "P3", "t2": "P4",
            "t4": "P1", "t6": "P4", "t9": "P2", "t8": "P4", "t10": "P2",
        })
        self.assertEqual(result["metrics"]["makespan"], 46)
        self.assertEqual(result["metrics"]["execution_cost"], 64)
        self.assertEqual(chromosome, original)

    def test_invalid_structure_and_ids_are_rejected(self):
        cases = (
            (None, "exactly two portions"),
            ((), "exactly two portions"),
            ((FIGURE_5_D,), "exactly two portions"),
            ((FIGURE_5_D, FIGURE_5_O, FIGURE_5_D), "exactly two portions"),
            ((None, FIGURE_5_O), "tuples or lists"),
            ((FIGURE_5_D, None), "tuples or lists"),
            ((FIGURE_5_D[:-1], FIGURE_5_O), "exactly 10 entries"),
            ((FIGURE_5_D + ("P1",), FIGURE_5_O), "exactly 10 entries"),
            ((FIGURE_5_D, FIGURE_5_O[:-1]), "exactly 10 entries"),
            ((FIGURE_5_D, FIGURE_5_O + ("t1",)), "exactly 10 entries"),
            ((FIGURE_5_D, ("t1",) + FIGURE_5_O[:-1]), "duplicate or missing"),
            ((FIGURE_5_D, ("t11",) + FIGURE_5_O[1:]), "unknown task ID"),
            ((("P5",) + FIGURE_5_D[1:], FIGURE_5_O), "Every entry in D"),
        )
        for chromosome, message in cases:
            with self.subTest(message=message, chromosome=chromosome):
                with self.assertRaisesRegex(ValueError, message):
                    validate_chromosome(chromosome)

    def test_published_precedence_violations_are_rejected(self):
        for parent, child, _ in problem.COMMUNICATION_EDGES:
            invalid_order = list(problem.TASK_IDS)
            parent_position = invalid_order.index(parent)
            child_position = invalid_order.index(child)
            invalid_order[parent_position], invalid_order[child_position] = (
                invalid_order[child_position], invalid_order[parent_position]
            )
            with self.subTest(edge=(parent, child)):
                with self.assertRaisesRegex(ValueError, "violates precedence"):
                    validate_chromosome((FIGURE_5_D, tuple(invalid_order)))

    def test_random_topological_orders_are_valid(self):
        rng = random.Random(2026)
        for _ in range(100):
            order = random_topological_order(rng)
            self.assertIsInstance(order, tuple)
            self.assert_valid_order(order)

    def test_random_processor_distributions_have_valid_positions(self):
        rng = random.Random(2026)
        for _ in range(100):
            distribution = random_processor_distribution(rng)
            self.assertIsInstance(distribution, tuple)
            self.assertEqual(len(distribution), 10)
            self.assertTrue(all(processor in problem.PROCESSOR_IDS for processor in distribution))

    def test_250_generated_chromosomes_validate_and_schedule(self):
        rng = random.Random(2026)
        for candidate_index in range(250):
            with self.subTest(candidate=candidate_index):
                chromosome = generate_random_chromosome(rng)
                distribution, order = chromosome
                self.assertIsInstance(chromosome, tuple)
                self.assertIsInstance(distribution, tuple)
                self.assertIsInstance(order, tuple)
                self.assertEqual(len(distribution), 10)
                self.assertTrue(all(processor in problem.PROCESSOR_IDS for processor in distribution))
                self.assert_valid_order(order)
                self.assertIs(validate_chromosome(chromosome), True)
                result = schedule(chromosome)
                self.assertEqual(len(result["trace"]), 10)
                self.assertEqual(result["task_assignments"], dict(zip(order, distribution)))
                self.assertEqual(tuple(row["task"] for row in result["trace"]), order)
                self.assertEqual(tuple(row["processor"] for row in result["trace"]), distribution)
                self.assertGreater(result["metrics"]["makespan"], 0)

    def test_same_seed_replays_the_same_sequence(self):
        first_rng = random.Random(42)
        second_rng = random.Random(42)
        for _ in range(20):
            self.assertEqual(generate_random_chromosome(first_rng),
                             generate_random_chromosome(second_rng))
        self.assertEqual(first_rng.getstate(), second_rng.getstate())

    def test_a_different_seed_can_change_the_output(self):
        first = generate_random_chromosome(random.Random(42))
        second = generate_random_chromosome(random.Random(43))
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
