"""
find a lit at level and recurse down tree
"""

import util
from concurrent.futures import ProcessPoolExecutor
import argparse
import multiprocessing
import random
import os


def config_to_string(args):
    out = "cnf: {} ".format(args.cnf)
    out += "cutoff: {} ".format(args.cutoff)
    out += "cube size: {}".format(args.cube_size)
    out += "cutoff time: {}".format(args.cutoff_time)
    out += "num samples: {}".format(args.num_samples)
    out += "dynamic depth: {}".format(args.dynamic_depth)
    return out


def find_cube_rec(args):
    finals = []
    todo = [[]]
    log_file = open(args.log, "a")
    depth = 0
    while depth < args.dynamic_depth:
        depth += 1
        procs = []
        while todo != []:
            current_cube = todo.pop()
            cnf = util.add_cube_to_cnf(args.cnf, current_cube, tmp=args.tmp_dir)
            proc = util.executor_sat.submit(
                util.run_cadical_lits,
                cnf,
                1,
                0,
                0,
                args.cutoff,
                False,
                1,
                sat_mode=args.sat_mode,
            )
            procs.append((proc, current_cube, cnf))
        for proc, cc, cnf in procs:
            output = proc.result().stdout.decode("utf-8").strip()
            try:
                lit_line = util.parse_lit_line_ext(output)
            except:
                print("failure")
                print(output)
                exit(1)
            split_lit = lit_line.lit
            time = lit_line.runtime
            log_file.write("c cube time (dynamic): {:2f}\n".format(time))
            log_file.flush()
            os.remove(cnf)
            if time < args.cutoff_time:
                finals.append(cc)
            else:
                todo.append(cc + [split_lit])
                todo.append(cc + [-split_lit])
    return (todo, finals)


def find_cube_sum(args, init_cube):
    result = []
    todo = [init_cube]
    log_file = open(args.log, "a")
    while todo != []:
        print("Cycling")
        procs = []
        if args.num_samples > len(todo):
            samples = todo
        else:
            samples = random.sample(todo, args.num_samples)
        for sample in samples:
            cnf = util.add_cube_to_cnf(args.cnf, sample, tmp=args.tmp_dir)
            proc = util.executor_sat.submit(
                util.run_cadical_litset,
                cnf,
                1,
                args.cutoff,
                args.lit_set_size,
                1,
                sat_mode=args.sat_mode,
            )
            procs.append((proc, sample, cnf))

        combined_dict = {}
        for proc, cc, cnf in procs:
            output = proc.result().stdout.decode("utf-8").strip()
            os.remove(cnf)
            lit_count_dict, time = util.parse_lit_set_ext(output)

            log_file.write(f"c cube time (static): {time}\n")
            log_file.flush()
            if time <= args.cutoff_time or len(lit_count_dict) <= args.lit_set_size / 2:
                result.append(cc)
                print(cc, "not good enough")
                try:
                    todo.remove(cc)
                except:
                    print(cc, todo)
                    exit(1)

                if todo == []:
                    break

                replacement_sample = []
                found = False
                for _ in range(10):
                    replacement_sample = random.choice(todo)
                    if replacement_sample not in samples:
                        found = True
                        break
                if found == False:
                    continue
                print("resampling with", replacement_sample)
                samples.append(replacement_sample)
                cnf = util.add_cube_to_cnf(
                    args.cnf, replacement_sample, tmp=args.tmp_dir
                )
                proc = util.executor_sat.submit(
                    util.run_cadical_litset,
                    cnf,
                    1,
                    args.cutoff,
                    args.lit_set_size,
                    1,
                )
                procs.append((proc, replacement_sample, cnf))
            else:
                for lit, score in lit_count_dict.items():
                    if lit in combined_dict:
                        combined_dict[lit] += score
                    else:
                        combined_dict[lit] = score
        try:
            split_lit = max(combined_dict, key=combined_dict.get)
        except:
            return result
        new_todo = []
        for cc in todo:
            if len(cc) + 1 < args.cube_size:
                new_todo.append(cc + [split_lit])
                new_todo.append(cc + [-split_lit])
            else:
                result.append(cc + [split_lit])
                result.append(cc + [-split_lit])
        todo = new_todo
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cnf", dest="cnf", required=True)
    parser.add_argument("--cube-size", dest="cube_size", type=int, required=True)
    parser.add_argument("--cutoff", dest="cutoff", type=int, required=True)
    parser.add_argument("--log", dest="log", required=True)
    parser.add_argument("--icnf", dest="icnf", default=None)
    parser.add_argument("--tmp-dir", dest="tmp_dir", default="tmp")
    parser.add_argument(
        "--cube-procs",
        dest="cube_procs",
        type=int,
        default=multiprocessing.cpu_count() - 2,
    )
    parser.add_argument(
        "--solve-procs",
        dest="solve_procs",
        type=int,
        default=multiprocessing.cpu_count() - 2,
    )
    parser.add_argument(
        "--cube-only",
        dest="cube_only",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    parser.add_argument(
        "--dynamic-depth", dest="dynamic_depth", type=int, required=True
    )
    parser.add_argument("--cutoff-time", dest="cutoff_time", type=float, default=1)

    parser.add_argument("--num-samples", dest="num_samples", type=int, default=32)

    parser.add_argument("--lit-set-size", dest="lit_set_size", type=int, default=32)
    parser.add_argument("--sat-mode", dest="sat_mode", type=int, default=-1)
    args = parser.parse_args()

    util.executor_sat = ProcessPoolExecutor(max_workers=args.cube_procs)

    os.makedirs(args.tmp_dir, exist_ok=True)
    try:
        os.makedirs(os.path.dirname(args.log), exist_ok=True)
    except:
        pass
    todo, final = find_cube_rec(args)
    for cc in todo:
        final += find_cube_sum(args, cc)

    util.executor_sat = ProcessPoolExecutor(max_workers=args.solve_procs)
    final_hc = final
    if args.icnf != None:
        util.make_icnf(final_hc, args.icnf)
    if not args.cube_only:
        util.run_hypercube(args.cnf, final_hc, args.log, tmp=args.tmp_dir)
