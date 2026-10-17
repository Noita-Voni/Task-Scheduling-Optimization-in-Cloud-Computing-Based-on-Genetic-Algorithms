"""Permanent Phase 4.2 checks using only the published problem instance."""

from copy import deepcopy
import unittest

import problem
from scheduler import schedule


FIGURE_5_D = ("P4", "P1", "P1", "P3", "P4", "P1", "P4", "P2", "P4", "P2")
FIGURE_5_O = ("t1", "t3", "t5", "t7", "t2", "t4", "t6", "t9", "t8", "t10")


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.original_data = deepcopy(self.problem_data())

    def tearDown(self):
        self.assertEqual(self.problem_data(), self.original_data)

    def problem_data(self):
        return (
            problem.TASK_IDS,
            problem.PROCESSOR_IDS,
            problem.COMPUTATION_DURATIONS,
            problem.PROCESSOR_RATES,
            problem.COMMUNICATION_EDGES,
        )

    def assert_schedule_constraints(self, result):
        rows = result["trace"]
        by_task = {row["task"]: row for row in rows}
        self.assertEqual(len(rows), 10)
        self.assertEqual(set(by_task), set(problem.TASK_IDS))
        for parent, child, published_delay in problem.COMMUNICATION_EDGES:
            parent_row, child_row = by_task[parent], by_task[child]
            delay = 0 if parent_row["processor"] == child_row["processor"] else published_delay
            self.assertGreaterEqual(child_row["start"], parent_row["finish"] + delay)
            detail = next(item for item in child_row["predecessors"] if item["task"] == parent)
            self.assertEqual(detail["processor"], parent_row["processor"])
            self.assertEqual(detail["finish"], parent_row["finish"])
            self.assertEqual(detail["published_communication_delay"], published_delay)
            self.assertEqual(detail["effective_communication_delay"], delay)
            self.assertEqual(detail["arrival"], parent_row["finish"] + delay)
        for processor in problem.PROCESSOR_IDS:
            local_rows = [row for row in rows if row["processor"] == processor]
            for previous, following in zip(local_rows, local_rows[1:]):
                self.assertGreaterEqual(following["start"], previous["finish"])
        for row in rows:
            task_index = problem.TASK_IDS.index(row["task"])
            processor_index = problem.PROCESSOR_IDS.index(row["processor"])
            self.assertEqual(row["finish"] - row["start"],
                             problem.COMPUTATION_DURATIONS[task_index][processor_index])
            self.assertEqual(row["processor_rate"], problem.PROCESSOR_RATES[row["processor"]])
            self.assertEqual(row["execution_charge"], row["duration"] * row["processor_rate"])
        self.assertEqual(result["metrics"]["execution_cost"], sum(
            busy * problem.PROCESSOR_RATES[processor]
            for processor, busy in result["metrics"]["processor_busy_times"].items()
        ))

    def test_figure_5_full_trace_and_metrics(self):
        chromosome = (FIGURE_5_D, FIGURE_5_O)
        original_chromosome = deepcopy(chromosome)
        result = schedule(chromosome)
        fields = ("task", "processor", "data_ready", "processor_ready",
                  "start", "finish", "duration", "execution_charge")
        expected_rows = [
            ("t1", "P4", 0, 0, 0, 3, 3, 6),
            ("t3", "P1", 6, 0, 6, 10, 4, 4),
            ("t5", "P1", 10, 10, 10, 15, 5, 5),
            ("t7", "P3", 16, 0, 16, 21, 5, 10),
            ("t2", "P4", 3, 3, 3, 7, 4, 8),
            ("t4", "P1", 23, 15, 23, 25, 2, 2),
            ("t6", "P4", 33, 7, 33, 34, 1, 2),
            ("t9", "P2", 30, 0, 30, 31, 1, 7),
            ("t8", "P4", 34, 34, 34, 37, 3, 6),
            ("t10", "P2", 44, 31, 44, 46, 2, 14),
        ]
        self.assertEqual([tuple(row[field] for field in fields) for row in result["trace"]],
                         expected_rows)
        self.assertEqual(result["metrics"]["makespan"], 46)
        self.assertEqual(result["metrics"]["execution_cost"], 64)
        self.assertEqual(result["metrics"]["processor_busy_times"],
                         {"P1": 11, "P2": 3, "P3": 5, "P4": 11})
        self.assertAlmostEqual(result["metrics"]["paper_aggregate_utilisation_pct"], 100 * 30 / 46)
        self.assertAlmostEqual(result["metrics"]["mean_processor_utilisation_pct"], 100 * 30 / 184)
        self.assert_schedule_constraints(result)
        self.assertEqual(schedule(chromosome), result)
        self.assertEqual(chromosome, original_chromosome)

    def test_all_tasks_on_p1(self):
        result = schedule((("P1",) * 10, problem.TASK_IDS))
        self.assertEqual([(row["start"], row["finish"]) for row in result["trace"]],
                         [(0, 4), (4, 7), (7, 11), (11, 13), (13, 18),
                          (18, 23), (23, 24), (24, 25), (25, 29), (29, 32)])
        self.assertEqual(result["metrics"], {
            "makespan": 32,
            "processor_busy_times": {"P1": 32, "P2": 0, "P3": 0, "P4": 0},
            "execution_cost": 32,
            "paper_aggregate_utilisation_pct": 100.0,
            "mean_processor_utilisation_pct": 25.0,
        })
        self.assert_schedule_constraints(result)

    def test_all_tasks_on_p2(self):
        result = schedule((("P2",) * 10, problem.TASK_IDS))
        self.assertEqual([(row["start"], row["finish"]) for row in result["trace"]],
                         [(0, 4), (4, 9), (9, 11), (11, 12), (12, 15),
                          (15, 16), (16, 18), (18, 19), (19, 20), (20, 22)])
        self.assertEqual(result["metrics"], {
            "makespan": 22,
            "processor_busy_times": {"P1": 0, "P2": 22, "P3": 0, "P4": 0},
            "execution_cost": 154,
            "paper_aggregate_utilisation_pct": 100.0,
            "mean_processor_utilisation_pct": 25.0,
        })
        self.assert_schedule_constraints(result)

    def test_invalid_supplied_chromosomes_are_rejected(self):
        cases = (
            ((FIGURE_5_D[:-1], FIGURE_5_O), "10 entries"),
            ((FIGURE_5_D, ("t1",) + FIGURE_5_O[:-1]), "exactly once"),
            ((("P5",) + FIGURE_5_D[1:], FIGURE_5_O), "Every entry in D"),
            ((FIGURE_5_D, tuple(reversed(FIGURE_5_O))), "violates precedence"),
        )
        for chromosome, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    schedule(chromosome)


if __name__ == "__main__":
    unittest.main()
