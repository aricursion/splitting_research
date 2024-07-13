from concurrent.futures import ProcessPoolExecutor
import argparse
import time
import multiprocessing
import os
from util import CadicalResult, add_cube_to_cnf, find_units_to_split, run_cadical, cadical_parse_results
import util


def find_tree(args, current_cube: list[int], time_cutoff: float, prev_learned: int):
    log_file = open(args.all_log, "a")
    cnf_loc = str(args.cnf)

    current_cube_cnf_loc = add_cube_to_cnf(cnf_loc, current_cube)
    cur = time.time()
    if not args.unit_count:
        splitting_units = find_units_to_split(
            current_cube_cnf_loc, args.unit_count, args.unit_gap, args.unit_gap_grow, args.unit_start
        )
    else:
        splitting_units = util.find_units_to_split_cone(current_cube_cnf_loc, args.unit_count, args.unit_cone_size)
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
        pos_proc = util.executor_sat.submit(run_cadical, pos_cnf_loc, prev_learned)
        neg_proc = util.executor_sat.submit(run_cadical, neg_cnf_loc, prev_learned)
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
    best_pos_learned = best_pos_metric.learned
    best_neg_learned = best_neg_metric.learned

    best_max_time = max(best_pos_learned, best_neg_learned)
    if best_max_time >= 0.9 * prev_learned:
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

    if best_pos_learned > time_cutoff:
        find_tree(args, next_pos_cube, time_cutoff, best_pos_learned)

    if best_neg_learned > time_cutoff:
        find_tree(args, next_neg_cube, time_cutoff, best_neg_learned)


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
    parser.add_argument("--unit-cone", dest="unit_cone", type=bool, action=argparse.BooleanOptionalAction)
    parser.add_argument("--unit-cone-size", dest="unit_cone_size", type=int, default=5000)
    parser.add_argument("--max-timeout", dest="max_timeout", type=int, default=2e5)
    parser.add_argument("--min-time", dest="min_time", type=int, default=0)
    parser.add_argument("--all-log", dest="all_log", required=True)
    parser.add_argument("--best-log", dest="best_log", required=True)
    parser.add_argument("--procs", dest="procs", type=int, default=multiprocessing.cpu_count() - 2)
    args = parser.parse_args()

    util.executor_sat = ProcessPoolExecutor(max_workers=args.procs)

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
