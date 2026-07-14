from __future__ import annotations

from importlib.resources import files


def where() -> str:
    return str(files("certifi").joinpath("cacert.pem"))


def contents() -> str:
    return files("certifi").joinpath("cacert.pem").read_text(encoding="ascii")
