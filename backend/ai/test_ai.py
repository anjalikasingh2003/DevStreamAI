from ai_engine import analyze_failure

log = """
FileNotFoundError: [Errno 2] No such file or directory: 'config.json'
"""

code = """
with open("config.json") as f:
    data = f.read()
"""

resp = analyze_failure(log, code)
print(resp)
