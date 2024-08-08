import sys
import os

def parseFile(file_loc):
    f = open(file_loc, "r")
    lines = f.read()
    if "UNSATISFIABLE" in lines:
        return -1
    elif "solution checked against the original DIMACS file with correct cost" in lines:
        occ = lines.find("CPU time")
        time = float(lines[occ + len("CPU time"):].split("\n")[0].split(":")[1].split("s")[0])
        return time
    else:
        return -2  

s = 0
m = 0
for file in os.listdir(sys.argv[1]):
    if file != "success.txt" and file != "error.txt" and file != "timeout.txt":
        t = parseFile(os.path.join(sys.argv[1], file))
        s += t
        if t > m:
            m = t
print("sum time:", s)
print("max time:", m)
