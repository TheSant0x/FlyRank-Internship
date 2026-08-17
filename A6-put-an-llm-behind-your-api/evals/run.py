import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("LLM_STUB", "1")
from src.llm.service import classify

cases = json.loads(open(os.path.join(os.path.dirname(__file__), "cases.json"), encoding="utf-8").read())
failures = []
for case in cases:
    actual = classify(case["text"]).category.value
    if actual != case["category"]:
        failures.append({"text": case["text"], "expected": case["category"], "actual": actual})
print(f"{len(cases) - len(failures)}/{len(cases)} ({(len(cases)-len(failures))/len(cases):.0%}) category accuracy")
for failure in failures:
    print(json.dumps(failure))
raise SystemExit(1 if failures else 0)
