from concurrent.futures import ProcessPoolExecutor
import os 
import util
import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cnf", dest="cnf", required=True)
    parser.add_argument("--procs", dest="procs", type=int, required=True)
    parser.add_argument('-u','--units', nargs='+', required=True)
    parser.add_argument("--log", required=True)
    
    args = parser.parse_args()

    util.executor_sat = ProcessPoolExecutor(max_workers=args.procs)
    os.makedirs("tmp", exist_ok=True)
    locs = []
    for unit in args.units:
        new_loc_pos = util.add_cube_to_cnf(args.cnf, [int(unit)])
        new_loc_neg = util.add_cube_to_cnf(args.cnf, [-int(unit)])
        locs += [(new_loc_pos, int(unit)), (new_loc_neg, -int(unit))]
    procs = []
    for loc, lit in locs:
        proc = util.executor_sat.submit(util.run_cadical, loc)
        procs.append((proc, lit))

    log = open(args.log, "w")
    log.write(args.cnf + "\n")
    for (proc, lit) in procs:
        output = str(proc.result().stdout.decode("utf-8").strip())
        cadical_result = util.cadical_parse_results(output)
        cadical_result_string = util.cadical_result_to_string(cadical_result)
        log.write(str(lit) +":" + cadical_result_string + "\n")
        log.flush()
    
    for loc in locs:
        os.remove(loc)
    log.close()
        



