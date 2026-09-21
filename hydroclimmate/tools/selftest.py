#!/usr/bin/env python3
"""selftest.py — builds small synthetic NetCDF cases and checks hcm_check.py's
verdicts against what each case was constructed to show. Uses only a temp
directory; touches no project data. Run directly: `python3 selftest.py`.

Requires numpy and netCDF4 (see tools/README.md for the environment note).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
HCM_CHECK = HERE / "hcm_check.py"
MODELS_DIR = HERE.parent / "references/models"
sys.path.insert(0, str(HERE))
import _miniyaml  # noqa: E402


def _load_layer(pack_dir, stem):
    """Load `<stem>.yaml` if present, else `<stem>.json` (see SCHEMA.md: a pack declares
    its generation, and so which extension its curated layers use, in its manifest)."""
    yaml_path = pack_dir / f"{stem}.yaml"
    if yaml_path.is_file():
        return _miniyaml.load_file(yaml_path)
    json_path = pack_dir / f"{stem}.json"
    return json.loads(json_path.read_text()) if json_path.is_file() else None


def need_stack():
    try:
        import numpy  # noqa: F401
        import netCDF4  # noqa: F401
    except ImportError as exc:
        sys.exit(
            f"ERROR: {exc}. On clusters that use environment modules, load a Python "
            "environment that provides numpy and netCDF4 first, e.g.:\n"
            "  module load conda; conda activate <env-with-numpy-and-netcdf4>"
        )


def write_field(path, var, data, dims=("y", "x"), attrs=None):
    import netCDF4
    with netCDF4.Dataset(path, "w") as ds:
        for name, size in zip(dims, data.shape):
            ds.createDimension(name, size)
        v = ds.createVariable(var, data.dtype, dims)
        v[...] = data
        for k, val in (attrs or {}).items():
            v.setncattr(k, val)


def write_timeseries(path, var, data, attrs=None):
    import netCDF4
    attrs = dict(attrs or {})
    fill_value = attrs.pop("_FillValue", None)
    with netCDF4.Dataset(path, "w") as ds:
        ds.createDimension("time", data.shape[0])
        ds.createDimension("y", data.shape[1])
        ds.createDimension("x", data.shape[2])
        kwargs = {"fill_value": fill_value} if fill_value is not None else {}
        v = ds.createVariable(var, data.dtype, ("time", "y", "x"), **kwargs)
        v[...] = data
        for k, val in attrs.items():
            v.setncattr(k, val)


def run(*args):
    result = subprocess.run(
        [sys.executable, str(HCM_CHECK), *args],
        capture_output=True, text=True,
    )
    return result.returncode, result.stdout, result.stderr


def expect(condition, message):
    if not condition:
        print(f"FAIL: {message}")
        return False
    print(f"ok: {message}")
    return True


def main():
    need_stack()
    import numpy as np

    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        # Case 1: difference scales with a control field.
        control = np.linspace(0, 10, 100).reshape(10, 10)
        a = np.zeros((10, 10))
        b = a + control * 2.0
        write_field(tmp / "pairA_a.nc", "resp", a)
        write_field(tmp / "pairA_b.nc", "resp", b)
        write_field(tmp / "pairA_ctrl.nc", "ctrl", control)
        thresholds = tmp / "pairA_thresh.json"
        thresholds.write_text(json.dumps({"spearman_min": 0.9, "invariants_identical": True}))
        rc, out, err = run(
            "paired-response", "--a", str(tmp / "pairA_a.nc"), "--b", str(tmp / "pairA_b.nc"),
            "--var", "resp", "--control-file", str(tmp / "pairA_ctrl.nc"), "--control-var", "ctrl",
            "--thresholds", str(thresholds),
        )
        ok &= expect(rc == 0, "pairA (scales with control): exit code 0")
        ok &= expect("VERDICT scales_with_control: VERIFIED" in out, f"pairA: verdict VERIFIED\n{out}\n{err}")

        # Case 2: no relationship — difference is flat / random noise, not tied to control.
        rng = np.random.default_rng(0)
        b_flat = a + rng.normal(0, 1e-9, size=a.shape)  # effectively zero, unrelated to control
        write_field(tmp / "pairB_a.nc", "resp", a)
        write_field(tmp / "pairB_b.nc", "resp", b_flat)
        rc, out, err = run(
            "paired-response", "--a", str(tmp / "pairB_a.nc"), "--b", str(tmp / "pairB_b.nc"),
            "--var", "resp", "--control-file", str(tmp / "pairA_ctrl.nc"), "--control-var", "ctrl",
            "--thresholds", str(thresholds),
        )
        ok &= expect(rc == 0, "pairB (flat, no relationship): exit code 0")
        ok &= expect("VERDICT scales_with_control: VIOLATED" in out, f"pairB: verdict VIOLATED\n{out}\n{err}")

        # Case 3: a declared invariant is contaminated (should differ between A and B).
        invariant_a = np.ones((10, 10)) * 5.0
        invariant_b = invariant_a.copy()
        invariant_b[3, 3] = 999.0
        write_field(tmp / "pairC_a.nc", "resp", a)
        write_field(tmp / "pairC_b.nc", "resp", b)
        write_field(tmp / "pairC_inv_a.nc", "grid_area", invariant_a)
        write_field(tmp / "pairC_inv_b.nc", "grid_area", invariant_b)
        # invariants are read from the same --a/--b files, so put both vars in one file each
        import netCDF4
        for path, resp, inv in ((tmp / "pairC_a.nc", a, invariant_a), (tmp / "pairC_b.nc", b, invariant_b)):
            with netCDF4.Dataset(path, "w") as ds:
                ds.createDimension("y", 10)
                ds.createDimension("x", 10)
                v1 = ds.createVariable("resp", resp.dtype, ("y", "x"))
                v1[...] = resp
                v2 = ds.createVariable("grid_area", inv.dtype, ("y", "x"))
                v2[...] = inv
        rc, out, err = run(
            "paired-response", "--a", str(tmp / "pairC_a.nc"), "--b", str(tmp / "pairC_b.nc"),
            "--var", "resp", "--invariants", "grid_area",
            "--thresholds", str(thresholds),
        )
        ok &= expect(rc == 0, "pairC (contaminated invariant): exit code 0")
        ok &= expect("Invariant 'grid_area': DIFFERS between A and B" in out,
                     f"pairC: invariant reported as differing\n{out}\n{err}")
        ok &= expect("VERDICT invariants_identical: VIOLATED" in out,
                     f"pairC: verdict VIOLATED\n{out}\n{err}")

        # Case 4: accumulator with declared fill, monotone, no undeclared large negatives.
        acc = np.cumsum(np.ones((5, 4, 4)), axis=0)
        write_timeseries(tmp / "accumA.nc", "accum", acc, attrs={"_FillValue": -9999.0, "units": "mm"})
        threshA = tmp / "threshA.json"
        threshA.write_text(json.dumps({"monotone_expected": True, "large_negative_allowed": False}))
        rc, out, err = run(
            "accumulation-and-fill", "--files", str(tmp / "accumA.nc"), "--var", "accum",
            "--thresholds", str(threshA),
        )
        ok &= expect(rc == 0, "accumA (clean accumulator): exit code 0")
        ok &= expect("VERDICT monotone_expected: VERIFIED" in out, f"accumA: monotone VERIFIED\n{out}\n{err}")
        ok &= expect("VERDICT large_negative_allowed: VERIFIED" in out,
                     f"accumA: large_negative_allowed VERIFIED\n{out}\n{err}")

        # Case 5: accumulator with an undeclared large negative fill and a reset.
        acc2 = np.cumsum(np.ones((5, 4, 4)), axis=0)
        acc2[3, 0, 0] = -1e10
        acc2[4] = acc2[3]  # a reset: drop below the previous step
        acc2[4, 1, 1] = 0.0
        write_timeseries(tmp / "accumB.nc", "accum", acc2, attrs={})  # no _FillValue declared
        rc, out, err = run(
            "accumulation-and-fill", "--files", str(tmp / "accumB.nc"), "--var", "accum",
            "--thresholds", str(threshA),
        )
        ok &= expect(rc == 0, "accumB (undeclared fill + reset): exit code 0")
        ok &= expect("VERDICT monotone_expected: VIOLATED" in out, f"accumB: monotone VIOLATED\n{out}\n{err}")
        ok &= expect("VERDICT large_negative_allowed: VIOLATED" in out,
                     f"accumB: large_negative_allowed VIOLATED\n{out}\n{err}")
        ok &= expect("_FillValue/missing_value declared: False" in out,
                     f"accumB: fill not declared\n{out}\n{err}")

        # No-thresholds case: verdict must be UNVERIFIED but observations still printed.
        rc, out, err = run(
            "paired-response", "--a", str(tmp / "pairA_a.nc"), "--b", str(tmp / "pairA_b.nc"), "--var", "resp",
        )
        ok &= expect(rc == 0, "no-thresholds case: exit code 0")
        ok &= expect("UNVERIFIED" in out, f"no-thresholds case: UNVERIFIED\n{out}\n{err}")
        ok &= expect("Non-zero difference:" in out, f"no-thresholds case: observations still printed\n{out}\n{err}")

    if ok:
        print("\nALL SELFTESTS PASSED")
        return 0
    print("\nSELFTEST FAILURES ABOVE")
    return 1


def _write_paired_pair(tmp, var, other_var, a_val, b_val, control_val=None):
    """Two files each holding `var` and `other_var` (so --invariants/--switch checks can
    read both from the same --a/--b pair, as paired-response requires)."""
    import netCDF4
    import numpy as np
    a_path, b_path = tmp / "pack_a.nc", tmp / "pack_b.nc"
    for path, val in ((a_path, a_val), (b_path, b_val)):
        with netCDF4.Dataset(path, "w") as ds:
            ds.createDimension("y", 4)
            ds.createDimension("x", 4)
            v = ds.createVariable(var, "f8", ("y", "x"))
            v[...] = np.full((4, 4), val)
            v2 = ds.createVariable(other_var, "f8", ("y", "x"))
            v2[...] = np.zeros((4, 4))
    return a_path, b_path


def run_pack_selftests():
    """For each pack with a selftest.yaml/selftest.json, build the tiny synthetic
    fixtures its cases declare and assert FIRED on the faulty one, QUIET on the clean
    one. Fixtures
    are built on the fly in a temp directory; none are stored in the repository."""
    need_stack()
    import numpy as np

    ok = True
    pack_dirs = sorted(p for p in MODELS_DIR.iterdir() if p.is_dir()
                       and ((p / "selftest.yaml").is_file() or (p / "selftest.json").is_file()))
    if not pack_dirs:
        print("No pack selftest.yaml/selftest.json files found; nothing to run for --packs.")
        return True

    for pack_dir in pack_dirs:
        pack_name = pack_dir.name
        cases = (_load_layer(pack_dir, "selftest") or {}).get("cases", [])
        for case in cases:
            pid = case["pitfall_id"]
            for role, spec in (("faulty", case["faulty"]), ("clean", case["clean"])):
                kind = spec["kind"]
                with tempfile.TemporaryDirectory() as tmp:
                    tmp = Path(tmp)
                    if kind in ("untouched_var_diff", "exchanged_var_diff"):
                        a_path, b_path = _write_paired_pair(tmp, spec["var"], "other_var", 0.0, 0.3)
                        rc, out, err = run(
                            "paired-response", "--a", str(a_path), "--b", str(b_path),
                            "--var", spec["var"], "--pack", pack_name, "--switch", spec["switch"],
                        )
                        fired = "NOT ATTRIBUTABLE" in out
                    elif kind == "undeclared_large_negative_fill":
                        data = np.ones((3, 4, 4))
                        data[1, 0, 0] = -1e33
                        path = tmp / "fixture.nc"
                        write_timeseries(path, spec["var"], data, attrs={})
                        rc, out, err = run("accumulation-and-fill", "--files", str(path),
                                            "--var", spec["var"], "--pack", pack_name)
                        fired = "_FillValue/missing_value declared: False" in out and \
                            "Large-magnitude negative values (<= -10000): 0 cells" not in out
                    elif kind == "no_large_negative_or_fill_declared":
                        data = np.ones((3, 4, 4))
                        path = tmp / "fixture.nc"
                        write_timeseries(path, spec["var"], data, attrs={"_FillValue": -9999.0})
                        rc, out, err = run("accumulation-and-fill", "--files", str(path),
                                            "--var", spec["var"], "--pack", pack_name)
                        fired = "_FillValue/missing_value declared: False" in out
                    else:
                        print(f"FAIL: {pack_name}/{pid}/{role}: unrecognized fixture kind '{kind}'")
                        ok = False
                        continue
                    expect_fired = (role == "faulty")
                    label = f"{pack_name}/{pid}/{role} ({kind})"
                    if fired == expect_fired:
                        print(f"ok: {label}: {'FIRED' if fired else 'QUIET'} as expected")
                    else:
                        print(f"FAIL: {label}: expected {'FIRED' if expect_fired else 'QUIET'}, "
                              f"got {'FIRED' if fired else 'QUIET'}\n{out}\n{err}")
                        ok = False
    return ok


def run_yaml_selftests():
    """Every pack YAML file must load to the identical
    Python object under this repo's own strict-subset reader (_miniyaml.load) and under
    PyYAML's yaml.safe_load, when PyYAML is importable -- the whole point of writing a
    restricted subset is that both readers agree on every file this repo ships. Also a
    minimal round-trip check via _miniyaml.dump."""
    ok = True
    yaml_files = sorted(MODELS_DIR.rglob("*.yaml"))
    if not yaml_files:
        print("FAIL: no pack YAML files found (expected at least hrldas-noahmp's)")
        return False
    try:
        import yaml
        have_pyyaml = True
    except ImportError:
        have_pyyaml = False
        print("note: PyYAML not importable here; only the _miniyaml reader is exercised "
              "(the equivalence claim itself is not tested this run).")

    for path in yaml_files:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(MODELS_DIR)
        try:
            mini = _miniyaml.load(text)
        except _miniyaml.MiniYamlError as exc:
            print(f"FAIL: {rel}: _miniyaml could not parse it: {exc}")
            ok = False
            continue
        if have_pyyaml:
            pyy = yaml.safe_load(text)
            if pyy != mini:
                print(f"FAIL: {rel}: PyYAML and _miniyaml disagree on parsed content")
                ok = False
                continue
        redumped = _miniyaml.load(_miniyaml.dump(mini))
        if redumped != mini:
            print(f"FAIL: {rel}: _miniyaml.dump(load(x)) does not round-trip")
            ok = False
    if ok:
        print(f"ok: {len(yaml_files)} pack YAML files -- _miniyaml"
              + (" and PyYAML agree" if have_pyyaml else " parses cleanly")
              + ", and round-trip through _miniyaml.dump")
    return ok


if __name__ == "__main__":
    if "--packs" in sys.argv:
        sys.exit(0 if run_pack_selftests() else 1)
    if "--yaml" in sys.argv:
        sys.exit(0 if run_yaml_selftests() else 1)
    yaml_ok = run_yaml_selftests()
    base_rc = main()
    sys.exit(0 if (base_rc == 0 and yaml_ok) else 1)
