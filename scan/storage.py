"""Atomic writes for scanner state and generated reports."""
import json
import os
import pathlib
import tempfile


def write_text(path, value):
    path = pathlib.Path(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".jobscan-tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write(value)
        os.replace(tmp, path)
    except BaseException:
        pathlib.Path(tmp).unlink(missing_ok=True)
        raise


def write_json(path, value, **options):
    write_text(path, json.dumps(value, **options))
