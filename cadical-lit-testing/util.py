from dataclasses import dataclass
import subprocess
import time
import os
from itertools import product

executor_sat = None


@dataclass
class CadicalResult:
    time: float
    learned: int
    props: int


@dataclass
class CnfHeader:
    var_num: int
    clause_num: int


def parse_lit_line(line: str) -> int:
    return int(line.split(" ")[2])


def run_cadical_lits(cnf_loc: str, lit_count: int, lit_gap: int, lit_gap_grow: int, lit_start: int):
    p = subprocess.run(
        [
            "./cadical-lits",
            cnf_loc,
            "-q",
            "/dev/null",
            "--litprint",
            f"--litcount={lit_count}",
            f"--litgap={lit_gap}",
            f"--litgapgrow={lit_gap_grow}",
            f"--litstart={lit_start}",
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


def find_lits_to_split(cnf_loc: str, lit_count: int, lit_gap: int, lit_gap_grow: int, lit_start: int) -> list[int]:
    submitted_proc = executor_sat.submit(run_cadical_lits, cnf_loc, lit_count, lit_gap, lit_gap_grow, lit_start)
    output = str(submitted_proc.result().stdout.decode("utf-8")).strip()

    output_lines = output.split("\n")
    out_lits = []
    for line in output_lines:
        if "s SATISFIABLE" in line or "s UNSATISFIABLE" in line:
            continue
        out_lits.append(abs(parse_lit_line(line)))

    return out_lits


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

    out = f"p cnf {header.var_num} {new_num_clauses}\n"
    out += "\n".join(cnf_string.split("\n")[1:])

    for lit in cube:
        out += f"{lit} 0\n"

    f = open(f"tmp/{tag}.cnf", "w+")
    f.write(out)
    f.close()
    return f"tmp/{tag}.cnf"


def generate_hypercube(cube):
    pos_neg_pairs = [(num, -num) for num in cube]
    combinations = list(product(*pos_neg_pairs))
    return list(map(list, combinations))
