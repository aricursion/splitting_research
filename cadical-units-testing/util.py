from dataclasses import dataclass
import subprocess
from concurrent.futures import ProcessPoolExecutor
import time
from itertools import product
import os

executor_sat: ProcessPoolExecutor


@dataclass
class CadicalResult:
    time: float
    learned: int
    props: int

def cadical_result_to_string(c: CadicalResult):
    return "time: {}, learned: {}, props: {}".format(c.time, c.learned, c.props)

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


def run_cadical_units_cone(cnf_loc: str, unit_count: int, unit_cone_size: int):
    p = subprocess.run(
        [
            "./cadical-units",
            cnf_loc,
            "-q",
            "/dev/null",
            "--unitprint",
            f"--unitcount={unit_count}",
            "--unitcone",
            f"--unitconesize={unit_cone_size}",
            "--lrat",
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
        if "s SATISFIABLE" in line or "s UNSATISFIABLE" in line:
            continue
        out_units.append(abs(parse_unit_line(line)))

    return out_units


def find_units_to_split_cone(cnf_loc: str, unit_count: int, unit_cone_size: int) -> list[int]:
    submitted_proc = executor_sat.submit(run_cadical_units_cone, cnf_loc, unit_count, unit_cone_size)
    output = str(submitted_proc.result().stdout.decode("utf-8")).strip()

    output_lines = output.split("\n")
    out_units = []
    for line in output_lines:
        if "s SATISFIABLE" in line or "s UNSATISFIABLE" in line:
            continue
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


def run_hypercube(cnf_loc, hc, log_file_loc, timeout=99999):
    log_file = open(log_file_loc, "a")
    procs = []
    for cube in hc:
        new_cnf_loc = add_cube_to_cnf(cnf_loc, cube)
        proc = executor_sat.submit(run_cadical, new_cnf_loc, timeout)
        procs.append((proc, new_cnf_loc, cube))
    t = 0
    for proc, loc, cube in procs:
        output = str(proc.result().stdout.decode("utf-8").strip())
        cadical_result = cadical_parse_results(output)

        log_file.write(
            ",".join(list(map(str, cube)))
            + " time: {}, learned: {}, props: {}\n".format(
                cadical_result.time, cadical_result.learned, cadical_result.props
            )
        )
        log_file.flush()
        t += cadical_result.time
        os.remove(loc)
    log_file.write("sum time: {:.2f}".format(t))
    log_file.close()
