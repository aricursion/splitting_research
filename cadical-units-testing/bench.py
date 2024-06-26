from dataclasses import dataclass
import subprocess
from concurrent.futures import ProcessPoolExecutor
import argparse
import time
import multiprocessing
import os


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
    os.remove(cnf_loc)
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

    os.remove(cnf_loc)
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


def find_tree(args, current_cube: list[int], time_cutoff: float, prev_time: float):
    log_file = open(args.all_log, "a")
    cnf_loc = str(args.cnf)

    current_cube_cnf_loc = add_cube_to_cnf(cnf_loc, current_cube)
    cur = time.time()
    splitting_units = find_units_to_split(
        current_cube_cnf_loc, args.unit_count, args.unit_gap, args.unit_gap_grow, args.unit_start
    )
    unit_find_time = time.time() - cur

    if len(splitting_units) == 0:
        return

    log_file.write(f"# finding units time: {unit_find_time:.2f}\n")
    log_file.flush()

    print(splitting_units)
    procs = []
    metrics = {}
    for i, unit in enumerate(splitting_units):
        if unit in current_cube or -unit in current_cube:
            continue
        new_pos_cube = current_cube + [unit]
        new_neg_cube = current_cube + [-unit]
        pos_cnf_loc = add_cube_to_cnf(cnf_loc, new_pos_cube)
        neg_cnf_loc = add_cube_to_cnf(cnf_loc, new_neg_cube)
        pos_proc = executor_sat.submit(run_cadical, pos_cnf_loc, prev_time)
        neg_proc = executor_sat.submit(run_cadical, neg_cnf_loc, prev_time)
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

        metrics[npc[-1]] = (pos_cadical_result, neg_cadical_result)
        log_file.write(
            ",".join(list(map(str, npc)))
            + " time: {}, learned: {}, props: {}\n".format(
                pos_cadical_result.time, pos_cadical_result.learned, pos_cadical_result.props
            )
        )
        log_file.write(
            ",".join(list(map(str, nnc)))
            + " time: {}, learned: {}, props: {}\n".format(
                neg_cadical_result.time, neg_cadical_result.learned, neg_cadical_result.props
            )
        )
        log_file.flush()
    log_file.close()

    time_metrics = {var: max(res1.time, res2.time) for (var, (res1, res2)) in metrics.items()}
    best_splitting_var = min(time_metrics, key=time_metrics.get)
    best_pos_metric, best_neg_metric = metrics[best_splitting_var]
    best_pos_time = best_pos_metric.time
    best_neg_time = best_neg_metric.time

    best_max_time = max(best_pos_time, best_neg_time)
    if best_max_time >= 0.9 * prev_time:
        return

    next_pos_cube = current_cube + [best_splitting_var]
    next_neg_cube = current_cube + [-best_splitting_var]

    log_file = open(args.best_log, "a")
    log_file.write(
        ",".join(list(map(str, next_pos_cube)))
        + " time: {}, learned: {}, props: {}\n".format(
            best_pos_metric.time, best_pos_metric.learned, best_pos_metric.props
        )
    )
    log_file.write(
        ",".join(list(map(str, next_neg_cube)))
        + " time: {}, learned: {}, props: {}\n".format(
            best_neg_metric.time, best_neg_metric.learned, best_neg_metric.props
        )
    )
    log_file.flush()
    log_file.close()

    if best_pos_time > time_cutoff:
        find_tree(args, next_pos_cube, time_cutoff, best_pos_time)

    if best_neg_time > time_cutoff:
        find_tree(args, next_neg_cube, time_cutoff, best_neg_time)


def config_to_string(args):
    out = "cnf: {} ".format(args.cnf)
    out += "unit-gap: {} ".format(args.unit_gap)
    out += "unit-gap-grow: {} ".format(args.unit_gap_grow)
    out += "unit-start: {} ".format(args.unit_start)
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cnf", dest="cnf", required=True)
    parser.add_argument("--unit-count", dest="unit_count", type=int, required=True)
    parser.add_argument("--unit-gap", dest="unit_gap", type=int, default=100)
    parser.add_argument("--unit-gapgrow", dest="unit_gap_grow", type=int, default=1)
    parser.add_argument("--unit-start", dest="unit_start", type=int, default=5000)
    parser.add_argument("--max-timeout", dest="max_timeout", type=int, default=2e7)
    parser.add_argument("--min-time", dest="min_time", type=int, default=0)
    parser.add_argument("--all-log", dest="all_log", required=True)
    parser.add_argument("--best-log", dest="best_log", required=True)
    parser.add_argument("--procs", dest="procs", type=int, default=multiprocessing.cpu_count() - 2)
    args = parser.parse_args()

    executor_sat = ProcessPoolExecutor(max_workers=args.procs)

    os.makedirs("tmp", exist_ok=True)
    os.makedirs(os.path.dirname(args.all_log), exist_ok=True)
    os.makedirs(os.path.dirname(args.best_log), exist_ok=True)
    with open(args.all_log, "a") as f:
        f.write("# all data log\n")
        f.write("# {}\n".format(config_to_string(args)))
        f.close()
    with open(args.best_log, "a") as f:
        f.write("# best data log\n")
        f.write("# {}\n".format(config_to_string(args)))
        f.close()

    find_tree(args, [], args.min_time, args.max_timeout)
