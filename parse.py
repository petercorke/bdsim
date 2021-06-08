import re

text = """
 integrator -> JACOB0(puma) -> INV        -0->o PROD('**') -> GAIN(5) -> integrator
 integrator -> FKINE(puma) -> T2XYZ[0:2] -> XYPLOT
                           +-0->o TRDELTA -1->o
TIME() -> FUNCTION(circle)  -1->o
"""

tokens = re.compile(r"""(?P<ARROW>\+?-([0-9]+-)?>o?)|
                        (?P<BLOCK>\w+\([^)]+\))|
                        (?P<REFERENCE>\w+)""", re.X)
for line in text.split('\n'):
    print(line)
    for m in tokens.finditer(line):
        tok = [k for (k,v) in m.groupdict().items() if v is not None][0]
        print(m[0], m.start(0), tok)

#parser  (REFERENCE | ARROW | TEE | BLOCK, arrowtype: arrow | tee, arrow id, indent, str)