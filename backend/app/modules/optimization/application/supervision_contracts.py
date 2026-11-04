"""B05 internal ownership metadata; independent of B01 wire/input/result codecs."""
import re


def identity(value):
    if (not isinstance(value, dict) or set(value) != {"pid", "start_ticks"}
        or type(value["pid"]) is not int or value["pid"] <= 0
        or not isinstance(value["start_ticks"], str) or not value["start_ticks"].isdigit()):
        raise ValueError("Process identity requires PID and Linux start time")
    return value


def runtime_metadata(value, execution_ids):
    if not isinstance(value, dict):
        raise ValueError("Invalid runtime metadata")
    if set(value) == {"supervisor_stopped_at"}:
        return value  # B02 reader compatibility; ownership is unknown, not inferred.
    if (set(value) != {"runtime_version", "supervisor_stopped_at", "supervisor", "workers"}
        or type(value["runtime_version"]) is not int or value["runtime_version"] != 1
        or not isinstance(value["workers"], dict)):
        raise ValueError("Invalid runtime ownership envelope")
    owner = value["supervisor"]
    if owner is not None:
        if not isinstance(owner, dict) or set(owner) != {"token", "identity"} or not isinstance(owner["token"], str) or re.fullmatch(r"[a-f0-9]{32}", owner["token"]) is None:
            raise ValueError("Invalid supervisor claim")
        identity(owner["identity"])
    elif value["workers"]:
        raise ValueError("Workers have no supervisor owner")
    if any(key not in {str(i) for i in execution_ids} for key in value["workers"]):
        raise ValueError("Worker belongs to another comparison")
    for worker in value["workers"].values():
        if worker is not None:
            identity(worker)
    return value
