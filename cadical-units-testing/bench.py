"""
--unitcount           : number of units before exiting
--unitprint         : print units to stdout
--unitgap=<N>       : number of learned clauses between printed units
--unitgapgrow=<N>   : multiplier for gap after each printed unit
--unitstart=<N>     : number of learned clauses before unit priniting starts
"""

import os
import sys
from dataclasses import dataclass
import subprocess
from concurrent.futures import ProcessPoolExecutor

executor_sat = ProcessPoolExecutor(max_workers=23)


def parse_unit_line(line: str) -> int:
    int(line.split(" ")[2])


def run_cadical_units(cnf: str, unit_count: int, unit_gap: int, unit_gap_grow: int, unit_start: int):
    p = subprocess.run(
        [
            "./cadical-units",
            cnf,
            "/dev/null",
            "--unitprint",
            f"--unitcount={unit_count}",
            f"--unitgap={unit_gap}",
            f"--unitgapgrow={unit_gap_grow}",
            f"--unitstart={unit_start}",
        ],
        stdout=subprocess.PIPE,
    )
    return p


def run_cadical(cnf: str, timeout: int):
    try:
        p = subprocess.run(["cadical", cnf], stdout=subprocess.PIPE, timeout=int(timeout))
    except subprocess.TimeoutExpired:
        p = "FAILURE"
    return p


def find_units_to_split(cnf: str, unit_count: int, unit_gap: int, unit_gap_grow: int, unit_start: int):
    submitted_proc = executor_sat.submit(run_cadical_units, [cnf, unit_count, unit_gap, unit_gap_grow, unit_start])
    output = str(submitted_proc.result().stdout.decode("utf-8")).strip()

    output_lines = output.split("\n")
    out_units = []
    for line in output_lines:
        out_units.append(abs(parse_unit_line(line)))

    return out_units


@dataclass
class CadicalResult:
    time: float


def cadical_parse_results(cadical_output: str):
    pass


if __name__ == "__main__":
    pass
