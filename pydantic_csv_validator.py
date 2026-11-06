"""Optional educational Pydantic validator for PAH Fingerprint Lab CSV files.

It applies the same rules as the browser app (index.html): accepted units and
sample types, value formats, required columns, duplicate IDs, 200 rows, 2 MB.

Install: python -m pip install -r requirements.txt
Run:     python pydantic_csv_validator.py PAH_Fingerprint_Synthetic_Examples.csv
Demo:    python pydantic_csv_validator.py --demo-error
"""
import csv
import io
import re
import sys
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError, ValidationInfo, field_validator

ANALYTES = ("NAP", "ACY", "ACE", "FLU", "PHE", "ANT", "FLT", "PYR",
            "BAA", "CHR", "BBF", "BKF", "BAP", "DBA", "ICP", "BGP")
REQUIRED_COLUMNS = ("sample_id", "group", "sample_type", "unit", *(a.lower() for a in ANALYTES))
MAX_ROWS = 200
MAX_BYTES = 2 * 1024 * 1024

# Units after lowercasing, removing whitespace, and mapping μ→µ and ²→2 (same as the app).
WIPE_UNITS = {"µg/m2", "ug/m2", "mcg/m2", "µg/100cm2", "ug/100cm2", "mcg/100cm2"}
MATERIAL_UNITS = {"mg/kgtm", "mg/kgdm", "mg/kgdry", "mg/kgdrymatter", "mg/kgts"}

NUMBER = r"[+]?(?:\d+(?:[.,]\d+)?|[.,]\d+)"  # no exponents, no signs other than +
QUANTIFIED = re.compile(NUMBER, re.ASCII)
CENSORED = re.compile(rf"<\s*({NUMBER})", re.ASCII)
UNQUANTIFIED = re.compile(r"nd|n\.d\.|n\.d|nq|bg|<bg|<loq|na|n/a|-|--|not detected", re.IGNORECASE)


def unit_kind(unit: str) -> str | None:
    """Return 'wipe', 'material' or None for an unrecognized unit."""
    s = re.sub(r"\s+", "", str(unit or "").lower()).replace("μ", "µ").replace("²", "2")
    if s in WIPE_UNITS:
        return "wipe"
    if s in MATERIAL_UNITS:
        return "material"
    return None


def check_value(raw: str) -> None:
    """Raise ValueError if a cell is not blank, a number, or <LOQ."""
    v = raw.strip()
    if not v:
        return  # Missing, not zero.
    m = CENSORED.fullmatch(v)
    if m:
        if not float(m.group(1).replace(",", ".")) > 0:
            raise ValueError("a <LOQ value must have a positive, finite limit")
        return
    if UNQUANTIFIED.fullmatch(v):
        raise ValueError("non-quantified entries need an explicit limit such as <0.5 "
                         "(or be blank if truly missing)")
    if not QUANTIFIED.fullmatch(v):
        raise ValueError("must be a nonnegative number or <LOQ, e.g. <0.5")


class PAHSample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sample_id: str
    group: str
    sample_type: Literal["wipe", "material"]
    unit: str
    measurements: dict[str, str]

    @field_validator("sample_id")
    @classmethod
    def check_sample_id(cls, v: str) -> str:
        v = v.strip()
        if not 1 <= len(v) <= 80:
            raise ValueError("sample_id must contain 1–80 characters")
        return v

    @field_validator("sample_type", mode="before")
    @classmethod
    def normalize_sample_type(cls, v):
        return v.strip().lower() if isinstance(v, str) else v

    @field_validator("unit")
    @classmethod
    def check_unit(cls, v: str, info: ValidationInfo) -> str:
        kind = unit_kind(v)
        if kind is None:
            raise ValueError(f"unrecognized unit {v!r}")
        sample_type = info.data.get("sample_type")  # absent if sample_type itself failed
        if sample_type and sample_type != kind:
            raise ValueError(f"{v!r} is a {kind} unit, but sample_type is {sample_type!r}")
        return v

    @field_validator("measurements")
    @classmethod
    def check_measurements(cls, v: dict[str, str]) -> dict[str, str]:
        if set(v) != set(ANALYTES):
            raise ValueError("exactly the 16 EPA PAH analytes are required")
        problems = []
        for name in ANALYTES:
            try:
                check_value(v[name])
            except ValueError as e:
                problems.append(f"{name}: {e}")
        if problems:
            raise ValueError("; ".join(problems))
        return v


def describe(error: ValidationError) -> str:
    return "; ".join(f"{e['loc'][0] if e['loc'] else 'row'}: {e['msg']}" for e in error.errors())


def detect_delimiter(header_line: str) -> str:
    """Count commas and semicolons outside quotes, as the app does."""
    comma = semi = 0
    quoted = False
    for c in header_line:
        if c == '"':
            quoted = not quoted
        elif not quoted:
            comma += c == ","
            semi += c == ";"
    return ";" if semi > comma else ","


def validate_csv(path: str) -> int:
    with open(path, "rb") as f:
        data = f.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        print("File is larger than 2 MB.")
        return 1
    try:
        content = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        print("File is not valid UTF-8 text.")
        return 1
    first = next((line for line in content.splitlines() if line.strip()), None)
    if first is None:
        print("CSV is empty.")
        return 1

    rows = [r for r in csv.reader(io.StringIO(content), delimiter=detect_delimiter(first))
            if any(cell.strip() for cell in r)]
    header = [h.strip().lower() for h in rows[0]]
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        print("Missing columns: " + ", ".join(missing))
        return 1
    if len(set(header)) != len(header):
        print("Duplicate column names.")
        return 1
    body = rows[1:]
    if not body:
        print("CSV must contain a header and at least one sample row.")
        return 1
    if len(body) > MAX_ROWS:
        print(f"At most {MAX_ROWS} sample rows are accepted (found {len(body)}).")
        return 1

    count, errors, seen = 0, 0, set()
    for line_no, cells in enumerate(body, 2):
        problem = None
        if len(cells) != len(header):
            problem = f"expected {len(header)} cells, got {len(cells)} (check delimiter and quoting)"
        else:
            row = dict(zip(header, (c.strip() for c in cells)))
            if row["sample_id"] in seen:
                problem = f"duplicate sample_id {row['sample_id']}"
            else:
                try:
                    entry = PAHSample(
                        sample_id=row["sample_id"],
                        group=row["group"],
                        sample_type=row["sample_type"],
                        unit=row["unit"],
                        measurements={name: row[name.lower()] for name in ANALYTES},
                    )
                    seen.add(entry.sample_id)
                except ValidationError as e:
                    problem = describe(e)
        if problem:
            errors += 1
            print(f"Row {line_no}: {problem}")
        else:
            count += 1
    print(f"Valid samples: {count}; invalid samples: {errors}")
    return 1 if errors else 0


def demo_error() -> int:
    measurements = {name: "1.0" for name in ANALYTES}
    measurements["NAP"] = "-3"   # negative concentration
    measurements["ACY"] = "ND"   # not detected, but no LOQ given
    try:
        PAHSample(sample_id="DEMO", group="demo", sample_type="wipe",
                  unit="mg/kg TM",  # material unit on a wipe sample
                  measurements=measurements)
    except ValidationError as e:
        print("Expected validation errors (all reported together):\n")
        print(e)
        return 0
    print("Unexpected: demo sample passed validation.")
    return 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python pydantic_csv_validator.py FILE.csv | --demo-error")
        sys.exit(2)
    sys.exit(demo_error() if sys.argv[1] == "--demo-error" else validate_csv(sys.argv[1]))
