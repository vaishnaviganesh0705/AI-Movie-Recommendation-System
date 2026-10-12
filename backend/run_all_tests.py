import os
import sys
import time
import inspect
import importlib

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

TEST_MODULES = [
    "tests.test_timestamp_utils",
    "tests.test_subtitle_parser",
    "tests.test_retriever",
    "tests.test_intent_router",
    "tests.test_answer_validator",
    "tests.test_api_endpoints",
    "tests.test_regression_variety"
]


def main():
    print("=" * 65)
    print(" STREAMHUB MULTI-AGENT AUTOMATED TEST SUITE")
    print(f" Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)

    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    start_all = time.time()
    failures = []

    for mod_name in TEST_MODULES:
        print(f"\n>> Running Module: {mod_name}")
        try:
            mod = importlib.import_module(mod_name)
        except Exception as e:
            print(f"  [ERROR] Failed to import module {mod_name}: {e}")
            import traceback
            traceback.print_exc()
            failed_tests += 1
            continue

        # Find all test_* functions
        funcs = [
            (name, func) for name, func in inspect.getmembers(mod, inspect.isfunction)
            if name.startswith("test_")
        ]

        for name, func in funcs:
            total_tests += 1
            t0 = time.time()
            try:
                func()
                dur_ms = round((time.time() - t0) * 1000, 1)
                print(f"  [PASS] {name} ({dur_ms}ms)")
                passed_tests += 1
            except Exception as e:
                dur_ms = round((time.time() - t0) * 1000, 1)
                print(f"  [FAIL] {name} ({dur_ms}ms): {e}")
                failures.append((mod_name, name, str(e)))
                failed_tests += 1

    total_dur = round(time.time() - start_all, 2)
    print("\n" + "=" * 65)
    print(" TEST SUITE EXECUTION SUMMARY")
    print("=" * 65)
    print(f" Total Tests Run:  {total_tests}")
    print(f" Passed:           {passed_tests}")
    print(f" Failed:           {failed_tests}")
    print(f" Success Rate:     {round((passed_tests / total_tests) * 100, 1) if total_tests else 0}%")
    print(f" Total Duration:   {total_dur} seconds")
    print("=" * 65)

    if failures:
        print("\nFailures:")
        for mod_name, name, err in failures:
            print(f" - {mod_name}.{name}: {err}")
        sys.exit(1)
    else:
        print("\nAll unit and integration tests PASSED successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
