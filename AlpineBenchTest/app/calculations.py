"""Measurement validation and acceptance rules, independent of the interface."""
import math


def number(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Enter a finite number.")
    return result


def evaluate(step, values, limits):
    failures = []
    results = {}
    for field in step.get("fields", []):
        key = field["id"]
        if field["type"] == "check":
            results[key] = bool(values.get(key))
            if not results[key]:
                failures.append(field["label"])
        else:
            results[key] = number(values[key])
    if step["kind"] == "decay":
        seconds = number(values["elapsed_seconds"])
        if seconds < 60:
            raise ValueError("Wait at least 60 seconds between initial and final readings.")
        results["elapsed_seconds"] = seconds
        for sensor in step["sensors"]:
            initial, final = results[sensor + "_initial"], results[sensor + "_final"]
            vacuum = step.get("vacuum", False)
            if (vacuum and (initial > 0 or final > 0)) or (not vacuum and (initial < 0 or final < 0)):
                raise ValueError("Use negative vacuum readings and nonnegative pressure readings.")
            # Loss of vacuum is movement toward zero; rising pressure is retained as a negative decay.
            rate = ((final - initial) if vacuum else (initial - final)) * 60 / seconds
            results[sensor + "_difference"] = final - initial if vacuum else initial - final
            results[sensor + "_decay"] = rate
            passed = 0 <= rate < limits["decay"][sensor]
            results[sensor + "_pass"] = passed
            if not passed:
                failures.append(sensor + " decay")
        if step["id"] == "er1":
            for suffix in ("initial", "final"):
                if not limits["r5"][0] <= results["CV5_" + suffix] <= limits["r5"][1]:
                    failures.append("CV5 " + suffix + " outside 2.5–3.75 psi")
    elif step["id"] == "cv3":
        if not 0 < results["CV5_pressure"] < limits["cv3_max"]:
            failures.append("CV5 must be greater than 0 and less than 1.20 psi")
    elif step["id"] == "vac2":
        for sensor in step["sensors"]:
            for voltage, bounds in limits["voltage"].items():
                key = sensor + "_" + voltage + "V"
                passed = bounds[0] <= results[key] <= bounds[1]
                results[key + "_pass"] = passed
                if not passed:
                    failures.append(key + " outside acceptable range")
    return results, failures
