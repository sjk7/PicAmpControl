import sys
from pathlib import Path
from trace_ptt_sequence import (build_script, run_mdb, find_mdb, parse_trace,
                                validate_sequence, validate_trip, validate_swr1_1p5,
                                validate_frequency_ready, validate_band_coverage, validate_freq_ctr,
                                validate_freq_ctr_failure)

scenario_names = [None, "TEMPERATURE", "SWR1", "SWR2", "HWFAULT",
                  "CURRENT", "OVERDRIVE", "DRAIN", "SWR1_1P5", "FREQ_CTR",
                  "FREQ_CTR_FAIL"]

first_script = build_script()
suite_lines = first_script.splitlines()[:-1]
for index, scenario in enumerate(scenario_names[1:], 1):
    scenario_lines = build_script(trip_name=scenario).splitlines()
    suite_lines.append("reset")
    suite_lines.extend(scenario_lines[3:-1])

raw_output = run_mdb(mdb_path=find_mdb(), script="\n".join(suite_lines + ["quit"]))
chunks = raw_output.split("Resetting SFRs")
groups = [(index, parse_trace(chunk)) for index, chunk in enumerate(chunks)]
groups = [(marker, scenario_samples) for marker, scenario_samples in groups if scenario_samples]

print(f"Total non-empty groups: {len(groups)}")
for idx, (m, samples) in enumerate(groups):
    name = scenario_names[idx] if idx < len(scenario_names) else "EXTRA"
    print(f"Index {idx} -> Scenario: {name} (samples: {len(samples)})")

validate_sequence(groups[0][1])
validate_frequency_ready(groups[0][1], scenario_names[0])
for scenario, (_, scenario_samples) in zip(scenario_names[1:], groups[1:]):
    if scenario == "FREQ_CTR_FAIL":
        validate_freq_ctr_failure(scenario_samples)
    else:
        validate_frequency_ready(scenario_samples, scenario)
    if scenario == "SWR1_1P5":
        validate_swr1_1p5(scenario_samples)
    elif scenario == "FREQ_CTR":
        validate_freq_ctr(scenario_samples, scenario)
    else:
        validate_trip(scenario_samples, scenario)

print("ALL SUITE SCENARIOS PASSED SUCCESSFULLY!")
