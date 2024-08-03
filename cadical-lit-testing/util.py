from dataclasses import dataclass
import shutil
import os
import subprocess
import time
from itertools import product
from concurrent.futures import ProcessPoolExecutor

executor_sat: ProcessPoolExecutor


@dataclass
class CadicalResult:
    time: float
    learned: int
    props: int


@dataclass
class CnfHeader:
    var_num: int
    clause_num: int

@dataclass 
class LitLine:
    lit: int
    runtime: float
    props: int

def parse_lit_line(line: str) -> int:
    return int(line.split(" ")[2])

def parse_lit_line_ext(line: str):
    runtime = float(line.split("#")[1].split("runtime:")[-1])
    props = int(line.split("#")[2].split("props:")[-1])
    return LitLine(parse_lit_line(line), runtime, props)

def parse_lit_set(line: str):
    return eval(line[1:])


def run_cadical_lits(cnf_loc: str, lit_count: int, lit_gap: int, lit_gap_grow: int, lit_start: int, lit_recent: bool):
    cmd = [
        "./cadical-lits",
        cnf_loc,
        "-q",
        "/dev/null",
        "--litprint",
        f"--litcount={lit_count}",
        f"--litgap={lit_gap}",
        f"--litgapgrow={lit_gap_grow}",
        f"--litstart={lit_start}",
    ]

    if lit_recent:
        cmd.append("--litrecent")

    p = subprocess.run(cmd, stdout=subprocess.PIPE)
    return p


def run_cadical_litset(cnf_loc: str, lit_count: int, lit_start: int, lit_set_size:int):
    cmd = [
        "./cadical-lits",
        cnf_loc,
        "-q",
        "/dev/null",
        "--litprint",
        "--litset",
        f"--litcount={lit_count}",
        f"--litstart={lit_start}",
        f"--litsetsize={lit_set_size}",
    ]

    p = subprocess.run(cmd, stdout=subprocess.PIPE)
    return p
 
# no timeout by default
def run_cadical(cnf_loc: str, timeout: float =-1):
    try:
        if timeout > 0:
            p = subprocess.run(["cadical", cnf_loc], stdout=subprocess.PIPE, timeout=timeout)
        else:
            p = subprocess.run(["cadical", cnf_loc], stdout=subprocess.PIPE)
    except subprocess.TimeoutExpired:
        p = "FAILURE"

    return p


def find_lits_to_split(
    cnf_loc: str, lit_count: int, lit_gap: int, lit_gap_grow: int, lit_start: int, lit_recent: bool
) -> list[int]:
    submitted_proc = executor_sat.submit(
        run_cadical_lits, cnf_loc, lit_count, lit_gap, lit_gap_grow, lit_start, lit_recent
    )
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


def run_hypercube_from_cube(cnf_loc, cube, log_file_loc, timeout=-1):
    hc = generate_hypercube(cube)
    run_hypercube(cnf_loc, hc, log_file_loc, timeout=timeout)


def run_hypercube(cnf_loc, hc, log_file_loc, timeout=-1):
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

def make_icnf(cnf_loc, cubes, icnf_loc):
    cnf_file = open(cnf_loc, "r")
    icnf_file = open(icnf_loc, "a")
    cnf_file.readline()
    icnf_file.write("p inccnf\n")
    shutil.copyfileobj(cnf_file, icnf_file)
    for cube in cubes:
        icnf_file.write("a " + " ".join(map(str, cube)) + " 0\n")
    cnf_file.close()
    icnf_file.close()

