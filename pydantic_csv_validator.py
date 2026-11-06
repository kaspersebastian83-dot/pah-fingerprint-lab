"""Optional educational Pydantic validator for PAH Fingerprint Lab CSV files.

Install: python -m pip install "pydantic>=2,<3"
Run:     python pydantic_csv_validator.py PAH_Fingerprint_Synthetic_Examples.csv
Demo:    python pydantic_csv_validator.py --demo-error
"""
import csv
import io
import sys
from typing import Literal
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

ANALYTES = ("NAP","ACY","ACE","FLU","PHE","ANT","FLT","PYR",
            "BAA","CHR","BBF","BKF","BAP","DBA","ICP","BGP")

class PAHSample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sample_id: str
    group: str
    sample_type: Literal["wipe", "material"]
    unit: Literal["µg/m²","µg/100cm²","ug/m2","ug/100cm2","mg/kg TM","mg/kg DM"]
    measurements: dict[str, str]

    @model_validator(mode="after")
    def check_matrix_units(self):
        wipe = {"µg/m²","µg/100cm²","ug/m2","ug/100cm2"}
        material = {"mg/kg TM","mg/kg DM"}
        allowed = wipe if self.sample_type == "wipe" else material
        if self.unit not in allowed:
            raise ValueError("Sample matrix and concentration unit are incompatible")
        if not self.sample_id.strip():
            raise ValueError("sample_id cannot be empty")
        if set(self.measurements) != set(ANALYTES):
            raise ValueError("Exactly the 16 EPA PAH analytes are required")
        for name, raw in self.measurements.items():
            v = raw.strip()
            if not v:
                continue  # Missing, not zero.
            if v.startswith("<"):
                v = v[1:].strip()
                censored = True
            else:
                censored = False
            try:
                number = float(v)
            except ValueError:
                raise ValueError(f"{name}: use a numeric value or an explicit LOQ such as <0.5")
            if not (number >= 0 and number < float("inf")):
                raise ValueError(f"{name}: concentration/LOQ must be finite and nonnegative")
            if censored and number == 0:
                raise ValueError(f"{name}: LOQ must be greater than zero")
        return self

def validate_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        content = f.read()
    delimiter = ";" if content.splitlines()[0].count(";") > content.splitlines()[0].count(",") else ","
    rows = csv.DictReader(io.StringIO(content), delimiter=delimiter)
    count, errors = 0, 0
    for line_no, row in enumerate(rows, 2):
        try:
            entry = PAHSample(
                sample_id=row.get("sample_id", ""),
                group=row.get("group", ""),
                sample_type=row.get("sample_type", ""),
                unit=row.get("unit", ""),
                measurements={name: (row.get(name) or "").replace(",", ".") for name in ANALYTES}
            )
            count += 1
        except (ValidationError, ValueError) as e:
            errors += 1
            print(f"Row {line_no}: {e}")
    print(f"Valid samples: {count}; invalid samples: {errors}")
    return 1 if errors else 0

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python pydantic_csv_validator.py FILE.csv | --demo-error")
        sys.exit(2)
    if sys.argv[1] == "--demo-error":
        try:
            PAHSample(sample_id="DEMO", group="demo", sample_type="wipe",
                      unit="mg/kg TM", measurements={name: "-3" if name == "NAP" else "ND" for name in ANALYTES})
        except ValidationError as e:
            print("Expected validation error:\n", e)
    else:
        sys.exit(validate_csv(sys.argv[1]))
