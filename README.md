# Hamed & Alkinani task-scheduling reproduction

Phase 4.1 implements the fixed 10-task/4-processor instance from Tables 1–3 of
Hamed & Alkinani (2021), DOI: 10.32604/cmc.2021.018658. The input data are
transcribed from the supplied paper, not generated randomly.
Phase 4.1 is approved. Phase 4.2 adds deterministic scheduling and metric
calculation for a supplied positional chromosome.
Phase 4.2 is approved. Phase 4.3 adds random valid chromosome generation and
structural/precedence validation using caller-supplied RNG objects.

## Current project structure

```text
Project/
├── AGENTS.md
├── TSP_CMC_18658.pdf
├── PHASE_4_0_IMPLEMENTATION_READINESS_REPORT.md
├── README.md
├── problem.py
├── scheduler.py
├── chromosome.py
└── tests/
    ├── test_scheduler.py
    └── test_chromosome.py
```

The user approved Phase 4.0 and its paper-based corrections, including positional
chromosome pairing and whole-portion crossover. Those conventions are recorded for
later phases. The current implementation covers problem data, data validation,
deterministic scheduling, metrics, and random valid chromosome generation and
validation. Permanent tests use the actual published instance.

## Exact problem data

`TASK_IDS` is the ordered tuple `(t1, t2, t3, t4, t5, t6, t7, t8, t9, t10)`.
`PROCESSOR_IDS` is the ordered tuple `(P1, P2, P3, P4)`.

### Table 2: computation durations

`COMPUTATION_DURATIONS` is a tuple of ten row tuples. Rows follow `TASK_IDS`;
columns follow `PROCESSOR_IDS`, exactly as in Table 2 on printed page 3296.
For example, `COMPUTATION_DURATIONS[2][1]` is the duration of t3 on P2: **2**.
These values represent time, despite the paper calling them computation costs.

| Task | P1 | P2 | P3 | P4 |
|---|---:|---:|---:|---:|
| t1 | 4 | 4 | 4 | 3 |
| t2 | 3 | 5 | 5 | 4 |
| t3 | 4 | 2 | 5 | 5 |
| t4 | 2 | 1 | 4 | 4 |
| t5 | 5 | 3 | 5 | 4 |
| t6 | 5 | 1 | 3 | 1 |
| t7 | 1 | 2 | 5 | 4 |
| t8 | 1 | 1 | 4 | 3 |
| t9 | 4 | 1 | 3 | 5 |
| t10 | 3 | 2 | 4 | 4 |

### Table 3: processor rates

`PROCESSOR_RATES` is a dictionary keyed by processor ID, from Table 3 on printed
page 3297. Rates are in unspecified monetary units per second; the implementation
does not assign a currency.

| Processor | Rate |
|---|---:|
| P1 | 1 |
| P2 | 7 |
| P3 | 2 |
| P4 | 2 |

### Table 1: dependencies and communication delays

`COMMUNICATION_EDGES` is a tuple of twelve `(parent, child, delay)` tuples.
The approved interpretation of Table 1 on printed page 3296 is **row = child,
column = parent**. For example, the 18 in row t2, column t1 becomes
`("t1", "t2", 18)`. All other zero cells mean absent edges for this published
instance. Explicit endpoints keep precedence distinct from delay values.

| Parent | Child | Delay |
|---|---|---:|
| t1 | t2 | 18 |
| t1 | t3 | 3 |
| t2 | t4 | 16 |
| t3 | t4 | 14 |
| t3 | t5 | 12 |
| t4 | t6 | 8 |
| t5 | t7 | 1 |
| t6 | t8 | 12 |
| t7 | t8 | 10 |
| t7 | t9 | 9 |
| t8 | t10 | 7 |
| t9 | t10 | 16 |

The stored delays remain the published edge weights. The scheduler calculates
effective delays from a supplied assignment without removing dependencies or
modifying these weights.

## Validation

Run with Python; the module uses only the standard library:

```powershell
python -B problem.py
```

`validate_problem()` reads the inputs, uses local graph structures to check for
cycles, and returns a summary. Invalid input raises `ValueError` with a reason.
It neither changes the inputs nor writes files. Its graph traversal is solely a
cycle check; it does not create task schedules or chromosomes.

The published instance passes these checks:

| Check | Result |
|---|---|
| Tasks | 10 unique IDs, t1–t10 |
| Processors | 4 unique IDs, P1–P4 |
| Duration matrix | 10 × 4; all 40 values positive integers |
| Processor rates | 4 positive integers, exactly one per processor |
| Communication edges | 12; all parent→child pairs unique |
| Endpoints | All belong to the task set |
| Self-loops | None |
| Communication delays | All non-negative integers; the published values are positive |
| Directed cycles | None |
| Source | t1 only |
| Sink | t10 only |

Structural validation cannot detect every otherwise valid transcription error.
The fixed values were additionally compared with Tables 1–3 of the supplied PDF.
The Phase 4.0 report records the table-orientation audit and distinguishes inputs
from inconsistent later results in the paper.

Verified with Python 3.13.2. All 40 durations, 12 directed edges and delays, and
4 rates matched the PDF transcription. Sixteen in-memory rejection checks passed,
covering missing/duplicate IDs, missing matrix rows or values, non-positive
durations/rates, missing rates or edges, invalid endpoints, duplicate edge pairs,
self-loops, negative delays, cycles, and incorrect sources/sinks. Validation left
the published inputs unchanged. The temporary in-memory copies were discarded;
no standalone verification scripts, fixtures, datasets or bytecode files were saved.

## Phase 4.2: deterministic scheduler

`scheduler.schedule((D, O))` uses positional pairing: task `O[k]` executes on
processor `D[k]`. The scheduler checks the supplied IDs, lengths and precedence
order, then processes O exactly as supplied. It does not generate or repair an
order, insert tasks into earlier idle gaps, or perform a search.

For each task, it records every predecessor's processor and finish time, the
published and effective communication delays, and the resulting arrival time.
Effective delay is zero for a same-processor dependency. Data-ready time is the
maximum predecessor arrival, or zero for a root. The task starts at the maximum
of that time and the assigned processor's current ready time; it finishes after
its Table 2 duration. The assigned processor's ready time then becomes that finish.

The return value has three entries:

- `task_assignments`: task-to-processor mapping decoded from `(D, O)`.
- `trace`: per-task dictionaries in the supplied construction order, including
  predecessor details, data readiness, processor readiness before placement,
  start, finish, duration, processor rate and execution charge.
- `metrics`: makespan, busy times, execution cost and both utilisation percentages.

`calculate_metrics(trace)` aggregates a completed trace separately from task
placement. Execution cost is the sum of `assigned duration × processor rate`.
Busy times count processing only, excluding waiting and communication delays.
With total busy time B, makespan C and all four processors counted:

```text
paper aggregate utilisation (%) = 100 × B / C
mean processor utilisation (%)  = 100 × B / (4 × C)
```

Neither utilisation definition is used as fitness. The scheduler uses only the
standard library and existing `problem.py` data. It does not change the inputs or
write files.

### Audited Figure 5 trace

The supplied chromosome is:

```text
D = (P4, P1, P1, P3, P4, P1, P4, P2, P4, P2)
O = (t1, t3, t5, t7, t2, t4, t6, t9, t8, t10)
```

Each predecessor expression below is `parent finish + effective delay = arrival`.
The trace retains the published delay separately, including when effective delay
is zero. The displayed task IDs follow the audited chromosome order rather than
the apparent sequential labelling error in the paper's Table 4.

| Task | Processor | Predecessor arrivals | Data ready | Processor ready | Start | Finish | Duration | Charge |
|---|---|---|---:|---:|---:|---:|---:|---:|
| t1 | P4 | None | 0 | 0 | 0 | 3 | 3 | 6 |
| t3 | P1 | t1: 3 + 3 = 6 | 6 | 0 | 6 | 10 | 4 | 4 |
| t5 | P1 | t3: 10 + 0 = 10 | 10 | 10 | 10 | 15 | 5 | 5 |
| t7 | P3 | t5: 15 + 1 = 16 | 16 | 0 | 16 | 21 | 5 | 10 |
| t2 | P4 | t1: 3 + 0 = 3 | 3 | 3 | 3 | 7 | 4 | 8 |
| t4 | P1 | t2: 7 + 16 = 23; t3: 10 + 0 = 10 | 23 | 15 | 23 | 25 | 2 | 2 |
| t6 | P4 | t4: 25 + 8 = 33 | 33 | 7 | 33 | 34 | 1 | 2 |
| t9 | P2 | t7: 21 + 9 = 30 | 30 | 0 | 30 | 31 | 1 | 7 |
| t8 | P4 | t6: 34 + 0 = 34; t7: 21 + 10 = 31 | 34 | 34 | 34 | 37 | 3 | 6 |
| t10 | P2 | t8: 37 + 7 = 44; t9: 31 + 0 = 31 | 44 | 31 | 44 | 46 | 2 | 14 |

The construction order does not force global serial execution: t2 on P4 can
start at time 3 even though it appears after t7 on P3 in O.

### Permanent validation cases

Run the retained tests with:

```powershell
python -B -m unittest discover -s tests -v
```

| Published-data case | Makespan | Cost | Busy times (P1,P2,P3,P4) | Paper aggregate (%) | Mean processor (%) |
|---|---:|---:|---|---:|---:|
| Figure 5 | 46 | 64 | (11,3,5,11) | 65.217391 | 16.304348 |
| All tasks on P1; O = TASK_IDS | 32 | 32 | (32,0,0,0) | 100 | 25 |
| All tasks on P2; O = TASK_IDS | 22 | 154 | (0,22,0,0) | 100 | 25 |

The tests compare Figure 5's complete timing and charge trace with the audited
values, check the all-P1/all-P2 intervals and metrics, and verify precedence,
processor non-overlap, predecessor details, correct duration lookup and consistent
cost aggregation. They also check deterministic replay, unchanged
inputs and rejection of invalid supplied chromosomes. These are validation cases,
not additional experiments. All four test methods passed with Python 3.13.2,
including the rejection checks for invalid supplied inputs. `problem.py` retained
its pre-implementation SHA-256 hash. No temporary validation fixtures were written,
and no synthetic problem data is retained.

## Phase 4.3: chromosome generation and validation

`chromosome.py` represents candidates as `(D, O)`, where both portions are tuples
of ten IDs. Task `O[k]` is assigned to processor `D[k]`; D is not indexed by task
ID. The module contains four functions:

| Function | Responsibility |
|---|---|
| `random_topological_order(rng)` | Generate a precedence-valid O directly from the published DAG |
| `random_processor_distribution(rng)` | Independently choose one of P1–P4 with equal probability at each of ten positions |
| `generate_random_chromosome(rng)` | Draw D first, then O, validate and return `(D, O)` |
| `validate_chromosome(chromosome)` | Return `True` if valid; otherwise raise `ValueError` |

At each topological-order step, ready tasks are the unscheduled tasks whose
predecessors have all been placed. The generator scans `TASK_IDS` to put ready
tasks in deterministic numeric ID order (`t1,t2,...,t10`), then uses `rng.choice`
to select the next task. It constructs a valid order without repairing an
arbitrary permutation or applying penalties. Uniform choice among ready tasks
does not necessarily sample all valid topological orders uniformly.

Processor choices are separate draws and do not depend on the task order or its
precedence relationships. All random functions require the caller's explicit RNG;
none creates a hidden generator, seeds it, or uses the module-global random state.
For example:

```python
from random import Random
from chromosome import generate_random_chromosome, validate_chromosome
from scheduler import schedule

rng = Random(42)
chromosome = generate_random_chromosome(rng)
validate_chromosome(chromosome)
result = schedule(chromosome)
```

Validation requires exactly two portions, ten entries in each, every published
task exactly once, valid task and processor IDs, and all twelve parent→child
precedence relationships. It calculates no timing, metrics or fitness. The existing
scheduler remains responsible for evaluating valid candidates.

The retained test suite checks Figure 5 acceptance and positional pairing,
malformed chromosome rejection, violations of each published precedence edge,
100 generated task orders, 100 processor distributions, and successful validation
and scheduling of 250 generated chromosomes on this fixed instance. It also checks
20-chromosome replay from separate `Random(42)` objects and confirms seeds 42 and
43 can produce different outputs without hard-coding a desired chromosome.
Published data and the module-global RNG state are checked for unchanged values.
All eight Phase 4.3 test methods and the four existing scheduler test methods
passed with Python 3.13.2 (12 tests total). The pre-implementation SHA-256 hashes
of both `problem.py` and `scheduler.py` were unchanged.

These are validation checks, not research experiments. Generated candidates exist
only in memory during the tests; no chromosome datasets, result exports, temporary
fixtures or verification scripts are saved. Run all permanent tests using the
existing command:

```powershell
python -B -m unittest discover -s tests -v
```

Phase 4.4 and all subsequent phases require separate user approval.
