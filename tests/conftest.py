"""Pytest configuration — writes plain text report to tests/results/python/report.txt."""

from pathlib import Path


def pytest_sessionfinish(session, exitstatus):
    results_dir = Path(__file__).parent / "results" / "python"
    results_dir.mkdir(parents=True, exist_ok=True)

    passed = session.testscollected - session.testsfailed
    lines = [
        f"Pytest Results — {session.startdir}",
        f"{'PASS' if exitstatus == 0 else 'FAIL'}: {passed}/{session.testscollected} passed",
        "",
    ]

    for item in session.items:
        rep = item.stash.get(_report_key, None)
        if rep:
            status = "PASS" if rep.passed else "FAIL"
            lines.append(f"  {status}: {item.nodeid}")

    report_path = results_dir / "report.txt"
    report_path.write_text("\n".join(lines) + "\n")


_report_key = None


def pytest_configure(config):
    global _report_key
    from _pytest.stash import StashKey
    _report_key = StashKey()


def pytest_runtest_makereport(item, call):
    if call.when == "call" and _report_key is not None:
        from _pytest.runner import TestReport
        rep = TestReport.from_item_and_call(item, call)
        item.stash[_report_key] = rep
