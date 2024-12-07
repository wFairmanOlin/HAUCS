import sys

print(sys.argv)
if len(sys.argv) > 1:
    timer_only = sys.argv[1]
else:
    timer_only = "false"

if timer_only.lower() == "true":
    print("only using timer")
else:
    print("using battery monitor")