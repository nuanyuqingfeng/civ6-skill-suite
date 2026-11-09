import sys
sys.path.insert(0, r"C:\\Users\\Administrator\\.agents\\skills\\civ6-tuner\\scripts")
import gamectl as G

s = G.Session()
if not s.connect():
    print("NO_CONNECT")
    raise SystemExit(1)
names = sorted(s.states)
print("N", len(names))
for n in names:
    print(n)
s.close()
