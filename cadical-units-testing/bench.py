"""
--unitcount           : number of units before exiting
--unitprint         : print units to stdout
--unitgap=<N>       : number of learned clauses between printed units
--unitgapgrow=<N>   : multiplier for gap after each printed unit
--unitstart=<N>     : number of learned clauses before unit priniting starts
"""

from dataclasses import dataclass
import subprocess
from concurrent.futures import ProcessPoolExecutor
import argparse

executor_sat = ProcessPoolExecutor(max_workers=23)


def parse_unit_line(line: str) -> int:
    return int(line.split(" ")[2])


def run_cadical_units(cnf_loc: str, unit_count: int, unit_gap: int, unit_gap_grow: int, unit_start: int):
    p = subprocess.run(
        [
            "./cadical-units",
            cnf_loc,
            "-q",
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


# no timeout by default
def run_cadical(cnf_loc: str, timeout=-1):
    try:
        if timeout > 0:
            p = subprocess.run(["cadical", cnf_loc], stdout=subprocess.PIPE, timeout=timeout)
        else:
            p = subprocess.run(["cadical", cnf_loc], stdout=subprocess.PIPE)
    except subprocess.TimeoutExpired:
        p = "FAILURE"
    return p


def find_units_to_split(cnf_loc: str, unit_count: int, unit_gap: int, unit_gap_grow: int, unit_start: int):
    submitted_proc = executor_sat.submit(run_cadical_units, cnf_loc, unit_count, unit_gap, unit_gap_grow, unit_start)
    output = str(submitted_proc.result().stdout.decode("utf-8")).strip()

    output_lines = output.split("\n")
    out_units = []
    for line in output_lines:
        out_units.append(abs(parse_unit_line(line)))

    return out_units


@dataclass
class CadicalResult:
    time: float
    learned: int
    props: int


def cadical_parse_results(cadical_output: str):
    stats_str = cadical_output.split("[ statistics ]")[-1].split("[ resources ]")[0]

    learned = int(stats_str[stats_str.find("learned") :].split(":")[1].split("per")[0].strip().split(" ")[0])
    props = int(stats_str[stats_str.find("propagations") :].split(":")[1].split("per")[0].strip().split(" ")[0])
    time_str = cadical_output.split("[ resources ]")[-1]
    time_loc = time_str.find("total process time since initialization")
    time_str = time_str[time_loc:]
    time = float(time_str.split(":")[1].split("seconds")[0].strip())

    return CadicalResult(time, learned, props)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cnf", dest="cnf", required=True)
    parser.add_argument("--unit-count", dest="unit_count", required=True)

    parser.add_argument("--unit-gap", dest="unit_gap", default=0)
    parser.add_argument("--unit-gapgrow", dest="unit_gapgrow", default=0)
    parser.add_argument("--unit-start", dest="unit_start", default=0)
    args = parser.parse_args()

    submitted_proc = executor_sat.submit(run_cadical, args.cnf)
    output = str(submitted_proc.result().stdout.decode("utf-8")).strip()

    print(cadical_parse_results(output))
