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
import time

executor_sat = ProcessPoolExecutor(max_workers=23)


@dataclass
class CadicalResult:
    time: float
    learned: int
    props: int


@dataclass
class CnfHeader:
    var_num: int
    clause_num: int


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


def find_units_to_split(cnf_loc: str, unit_count: int, unit_gap: int, unit_gap_grow: int, unit_start: int) -> list[int]:
    submitted_proc = executor_sat.submit(run_cadical_units, cnf_loc, unit_count, unit_gap, unit_gap_grow, unit_start)
    output = str(submitted_proc.result().stdout.decode("utf-8")).strip()

    output_lines = output.split("\n")
    out_units = []
    for line in output_lines:
        out_units.append(abs(parse_unit_line(line)))

    return out_units


def cadical_parse_results(cadical_output: str):
    stats_str = cadical_output.split("[ statistics ]")[-1].split("[ resources ]")[0]

    learned = int(stats_str[stats_str.find("learned") :].split(":")[1].split("per")[0].strip().split(" ")[0])
    props = int(stats_str[stats_str.find("propagations") :].split(":")[1].split("per")[0].strip().split(" ")[0])
    time_str = cadical_output.split("[ resources ]")[-1]
    time_loc = time_str.find("total process time since initialization")
    time_str = time_str[time_loc:]
    time = float(time_str.split(":")[1].split("seconds")[0].strip())

    return CadicalResult(time, learned, props)


def cnf_parse_header(cnf_string: str):
    header = cnf_string.split("\n")[0].split(" ")
    return CnfHeader(int(header[2]), int(header[3]))


def add_cube_to_cnf(cnf_loc: str, cube: list[int]):
    cnf_string = open(cnf_loc, "r").read()

    tag = (str(time.time()).split("."))[1]
    header = cnf_parse_header(cnf_string)
    new_num_clauses = header.clause_num + len(cube)

    out = f"p cnf {header.vars} {new_num_clauses}\n"
    out += "\n".join(cnf_string.split("\n")[1:])

    for lit in cube:
        out += f"{lit} 0\n"

    f = open(f"tmp/{tag}.wcnf", "w+")
    f.write(out)
    f.close()
    return f"tmp/{tag}.wcnf"


def find_tree(args, current_cube: list[int], cnf_loc: str, time_cutoff: str, log_file: str):
    log_file = open(log_file, "a")
    splitting_units = find_units_to_split(cnf_loc, args.unit_count, args.unit_gap, args.unit_gap_grow, args.unit_start)

    procs = []
    metrics = []
    for i, unit in enumerate(splitting_units):
        if unit in current_cube or -unit in current_cube:
            continue
        new_pos_cube = current_cube + [unit]
        new_neg_cube = current_cube + [-unit]
        pos_cnf_loc = add_cube_to_cnf(cnf_loc, new_pos_cube)
        neg_cnf_loc = add_cube_to_cnf(cnf_loc, new_neg_cube)
        pos_proc = executor_sat.submit(run_cadical, pos_cnf_loc, -1)  # TODO: Replace -1
        neg_proc = executor_sat.submit(run_cadical, neg_cnf_loc, -1)
        procs.append((pos_proc, neg_proc, new_pos_cube, new_neg_cube))

    for pos_proc, neg_proc, npc, nnc in procs:
        if pos_proc.result() == "FAILURE":
            pos_cadical_result = CadicalResult(9999, 9999, 9999)
        else:
            try:
                output = str(pos_proc.result().stdout.decode("utf-8")).strip()
                pos_cadical_result = cadical_parse_results(output)
            except Exception:
                pos_cadical_result = CadicalResult(8888, 8888, 8888)

        if neg_proc.result() == "FAILURE":
            neg_cadical_result = CadicalResult(9999, 9999, 9999)
        else:
            try:
                output = str(neg_proc.result().stdout.decode("utf-8")).strip()
                neg_cadical_result = cadical_parse_results(output)
            except Exception:
                neg_cadical_result = CadicalResult(8888, 8888, 8888)

        metrics.append((npc[-1], (pos_cadical_result, neg_cadical_result)))
        log_file.write(
            ",".join(list(map(str, npc)))
            + f" {time: pos_cadical_result.time, learned: pos_cadical_result.learned, props: pos_cadical_result.props}"
        )
        log_file.write(
            ",".join(list(map(str, nnc)))
            + f" {time: neg_cadical_result.time, learned: neg_cadical_result.learned, props: neg_cadical_result.props}"
        )
        log_file.flush()
    log_file.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cnf", dest="cnf", required=True)
    parser.add_argument("--unit-count", dest="unit_count", required=True)

    parser.add_argument("--unit-gap", dest="unit_gap", default=0)
    parser.add_argument("--unit-gapgrow", dest="unit_gap_grow", default=0)
    parser.add_argument("--unit-start", dest="unit_start", default=0)
    args = parser.parse_args()

    submitted_proc = executor_sat.submit(run_cadical, args.cnf)
    output = str(submitted_proc.result().stdout.decode("utf-8")).strip()

    print(cadical_parse_results(output))
