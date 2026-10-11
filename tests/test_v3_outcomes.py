import json
from scripts.v3_outcomes import disposition, FORMAT_FAILURES


def test_observed_format_abort_remains_failure_and_is_evaluated(tmp_path):
    row={"status":"failed","error":sorted(FORMAT_FAILURES)[0],"steps":2,"recovery_steps":None}
    (tmp_path/"requests.jsonl").write_text('\n'.join(json.dumps({"status":"ok"}) for _ in range(2)))
    assert disposition(row,tmp_path)=="method_terminated_format_failure"
    assert row["status"]=="failed" and row["recovery_steps"] is None


def test_transport_or_unverified_abort_is_incomplete(tmp_path):
    row={"status":"failed","error":sorted(FORMAT_FAILURES)[0]}
    (tmp_path/"requests.jsonl").write_text('{"status":"ok"}\n{"status":"unknown_billing"}\n')
    assert disposition(row,tmp_path)=="incomplete"
    assert disposition({"status":"failed","error":"TimeoutError"},tmp_path)=="incomplete"
