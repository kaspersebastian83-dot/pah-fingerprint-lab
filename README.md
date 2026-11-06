# PAH Fingerprint Lab · v0.1

**Live site (after GitHub Pages is enabled):** https://kaspersebastian83-dot.github.io/pah-fingerprint-lab/

To deploy on GitHub Pages: Settings → Pages → Build and deployment → Deploy from a branch; select `main` and `/ (root)`. The `index.html` at repository root is the browser app.

**Privacy:** This repository contains synthetic demonstration data only. Do not commit real client data, customer names, or lab reports to this public repository.


A self-contained, offline exploratory tool for comparing profiles of the **16 EPA priority PAHs**. Created for learning and research; **not** a validated forensic attribution tool.

## Run the app

1. Extract the ZIP file (if you downloaded the ZIP).
2. Double-click `PAH_Fingerprint_Lab.html` to open it in a current Chrome, Edge, Safari or Firefox browser. **No installation or Python required.**
3. Change Sample A and Sample B. Explore the `Relative %` and `Concentration` views; see `Σ16` bounds, four isomer ratios and PCA.
4. Move the LOQ slider between 0 and 1. For visualization, censored analytes are represented by that fraction of their LOQ. **This fraction is an assumption, not a measurement.**
5. Try the `Import CSV` button with `PAH_Fingerprint_Synthetic_Examples.csv`, or download the blank template from inside the app and enter your own values.
6. Use `Print / Save PDF` to save a printable overview of the currently selected pair.

## CSV layout

One row = one sample. Required metadata columns: `sample_id`, `group`, `sample_type`, `unit`. Required analyte columns:

`NAP, ACY, ACE, FLU, PHE, ANT, FLT, PYR, BAA, CHR, BBF, BKF, BAP, DBA, ICP, BGP`

Optional columns: `site`, `notes`. You may include all optional fields; unrecognized extra columns are ignored by the browser app.

- Accepted `sample_type` values: `wipe`, `material`.
- Accepted wipe units: `µg/m²`, `µg/100cm²` (also `ug/m2`, `ug/100cm2`). The app converts `µg/100cm²` to `µg/m²` by multiplying by 100.
- Accepted material units: `mg/kg TM`, `mg/kg DM`.
- An analyte cell is a quantified concentration (`4.3`), left-censored (`<0.5`), or blank (missing, **not** zero). A bare `ND` is rejected because its quantification limit is unknown.
- Both comma-separated CSV with decimal points, and semicolon-separated CSV with decimal commas are supported. Use the downloaded example as a formatting reference.
- The app accepts up to 200 rows and 2 MB of CSV data. Incorrect rows are reported and skipped; the import notice specifies how many were accepted.

**Important:** `Σ16` intervals use quantified results and 0–LOQ bounds for censored values. They are **not** confidence intervals. A missing analyte makes the full-sum upper bound unknown. Zero/half/full LOQ substitution can distort the ratios and PCA, especially when there are many censored observations.

## Interpretation limits

- The built-in examples are **invented profiles**, intentionally labelled synthetic. They are not empirical source-reference data and no inference about source chemistry should be drawn from their group separation.
- The app deliberately prevents **cross-matrix** comparisons (wipe vs material), including cosine similarity. Area conversion cannot correct for sampling-method differences.
- Diagnostic ratio bounds use numerator/denominator intervals. No published threshold is used to assign a source type.
- Shape similarity and PCA are exploratory mathematical descriptions; neither establishes common origin.
- PCA is calculated on normalized linear fractions of the 16 PAHs; this is a teaching prototype, not a validated chemometric workflow. No full treatment of measurement uncertainty or censor-aware multivariate inference is implemented.
- All data remains in the browser's memory. The app makes **no network requests and does not save, upload or sync data**.

## Optional: learn Pydantic in action

The browser app is **written in JavaScript, not Python**. The companion script `pydantic_csv_validator.py` demonstrates where Pydantic can help in a future Python workflow: validating the exact same CSV before doing any statistics.

With Python 3.10+ installed, run:

```bash
python3 -m pip install "pydantic>=2,<3"
python3 pydantic_csv_validator.py --demo-error
python3 pydantic_csv_validator.py PAH_Fingerprint_Synthetic_Examples.csv
```

The `--demo-error` example intentionally supplies an incorrect sample matrix/unit, a negative concentration and an unquantified `ND`, and Pydantic explains why they are invalid. You can inspect the `PAHSample`, `BelowLOQ`, and `Quantified` models in the script alongside your Python course.

## Scientific reading

- German Environmental Specimen Bank: [EPA-16 PAH list](https://www.umweltprobenbank.de/en/documents/13446)
- US EPA: [Censored environmental data considerations](https://www.epa.gov/n-steps-online/data-considerations)
- Tobiszewski & Namieśnik (2012): [PAH diagnostic ratios — limitations](https://pubmed.ncbi.nlm.nih.gov/22243855/)
- Katsoyiannis et al. (2011): [Critical evaluation of diagnostic ratios](https://pubmed.ncbi.nlm.nih.gov/21859122/)

Version 0.1 — exploratory learning software, not a certified laboratory, regulatory, or forensic decision system.