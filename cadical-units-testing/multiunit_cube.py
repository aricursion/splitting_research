import util
from concurrent.futures import ProcessPoolExecutor
import argparse
import multiprocessing
import os


def config_to_string(args):
    out = "cnf: {} ".format(args.cnf)
    out += "unit-gap: {} ".format(args.unit_gap)
    out += "unit-gap-grow: {} ".format(args.unit_gap_grow)
    out += "unit-start: {} ".format(args.unit_start)
    return out


def find_hypercube(args):
    log_file = open(args.log, "a")
    if not args.unit_cone:
        cube_units = util.find_units_to_split(
            args.cnf, args.cube_size, args.unit_gap, args.unit_gap_grow, args.unit_start
        )
    else:
        cube_units = util.find_units_to_split_cone(args.cnf, args.unit_count, args.unit_cone_size)
    hypercube = util.generate_hypercube(cube_units)
    procs = []
    for cube in hypercube:
        new_cnf_loc = util.add_cube_to_cnf(args.cnf, cube)
        proc = util.executor_sat.submit(util.run_cadical, new_cnf_loc, 999999)
        procs.append((proc, cube))
    for proc, cube in procs:
        try:
            output = str(proc.result().stdout.decode("utf-8")).strip()
            cadical_result = util.cadical_parse_results(output)
        except Exception:
            cadical_result = util.CadicalResult(8888, 8888, 8888)

        log_file.write(
            ",".join(list(map(str, cube)))
            + " time: {}, learned: {}, props: {}\n".format(
                cadical_result.time, cadical_result.learned, cadical_result.props
            )
        )
        log_file.flush()
    log_file.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cnf", dest="cnf", required=True)
    parser.add_argument("--cube-size", dest="cube_size", type=int, required=True)
    parser.add_argument("--unit-gap", dest="unit_gap", type=int, default=100)
    parser.add_argument("--unit-gapgrow", dest="unit_gap_grow", type=int, default=1)
    parser.add_argument("--unit-start", dest="unit_start", type=int, default=5000)
    parser.add_argument("--unit-cone", dest="unit_cone", type=bool, action=argparse.BooleanOptionalAction)
    parser.add_argument("--unit-cone-size", dest="unit_cone_size", type=int, default=5000)
    parser.add_argument("--log", dest="log", required=True)
    parser.add_argument("--procs", dest="procs", type=int, default=multiprocessing.cpu_count() - 2)
    args = parser.parse_args()

    util.executor_sat = ProcessPoolExecutor(max_workers=args.procs)
    os.makedirs("tmp", exist_ok=True)
    os.makedirs(os.path.dirname(args.log), exist_ok=True)
    with open(args.log, "a") as f:
        f.write("# cube log\n")
        f.write("# {}\n".format(config_to_string(args)))
        f.close()

    find_hypercube(args)
