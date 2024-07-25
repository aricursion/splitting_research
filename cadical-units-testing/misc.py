from concurrent.futures import ProcessPoolExecutor
import os
import util
import sys

util.executor_sat = ProcessPoolExecutor(10)

lits = [505, 425, 349, 332, 347, 348, 424, 331, 330, 346, 423, 345, 422]
lits = [ -207, 
 -504, 
 381, 
 350, 
 333, 
 271, 
 45, 
 -370, 
 -212 ]

cnf_loc = sys.argv[1]
log_file = open(sys.argv[2], "a")
results = []
procs = []
for lit in lits:
    hc = util.generate_hypercube([lit])
    # util.run_hypercube(sys.argv[1], hc, sys.argv[2])
    for cube in hc:
        new_cnf_loc = util.add_cube_to_cnf(cnf_loc, cube)
        proc = util.executor_sat.submit(util.run_cadical, new_cnf_loc)
        procs.append((proc, new_cnf_loc, cube))

for proc, loc, cube in procs:
    output = str(proc.result().stdout.decode("utf-8").strip())
    cadical_result = util.cadical_parse_results(output)

    log_file.write(
        ",".join(list(map(str, cube)))
        + " time: {}, learned: {}, props: {}\n".format(
            cadical_result.time, cadical_result.learned, cadical_result.props
        )
    )
    log_file.flush()
    os.remove(loc)
