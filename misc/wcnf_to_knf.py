import sys

def parse_line(line):
    split_line = line.strip().split(" ")
    weight = int(split_line[0])
    lits = list(map(int, split_line[1:-1]))
    return (weight, lits)

wcnf_file = open(sys.argv[1], "r")
header = wcnf_file.readline().strip()
split_header = header.split(" ")
num_vars = int(split_header[2])
num_clauses = int(split_header[3])
hard_weight = int(split_header[4])
knf_string = ""

constraint_lits = []
for line in wcnf_file.readlines():
    (weight, lits) = parse_line(line)
    if weight == hard_weight:
        knf_string += " ".join(map(str, lits)) + " 0\n"
    else:
        constraint_lits += lits

knf_file = open(sys.argv[2], "w")
knf_file.write("p knf {} {}\n".format(num_vars, num_clauses))
knf_file.write(knf_string)
knf_file.write("k {} {}\n".format(sys.argv[3], " ".join(map(lambda x: str(-x), constraint_lits))))
