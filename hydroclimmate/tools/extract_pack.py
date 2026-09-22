#!/usr/bin/env python3
"""extract_pack.py -- generic dispatcher for every `depth: reference` pack's mechanical
catalog extractors. Model-specific parsing logic lives entirely in a per-pack module
under tools/extractors/ (extractors/hrldas_noahmp.py, extractors/vic.py, ...); this file
knows nothing about Fortran, C, HRLDAS or VIC -- it only resolves --pack to a module,
runs the module's requested subcommand(s) against --source-root, and writes the result
(strict-subset YAML for catalog layers, JSON for the machine-only MANIFEST.json).

Usage:
  extract_pack.py [--pack PACK] SUBCOMMAND --source-root ROOT --out FILE.yaml
  extract_pack.py [--pack PACK] all         --source-root ROOT --out-dir catalogs/

--pack defaults to "hrldas-noahmp" (the pack this tool originally shipped for), so every
pre-existing invocation of this command (see hrldas-noahmp/pack.yaml's own `regenerate`
field and SCHEMA.md) is unchanged and regenerates that pack's catalogs byte-identically.
For another pack, pass --pack explicitly, e.g.:
  extract_pack.py --pack vic all --source-root <pinned-VIC-checkout> \\
      --out-dir hydroclimmate/references/models/vic/catalogs

Each per-pack module exposes: PACK (str), GENERATOR_VERSION (str), SCOPE (str),
SOURCE_COMMITS (dict), CATALOGS ({subcommand: callable(root) -> dict}),
FILENAME ({subcommand: output filename}), and write_yaml(obj, out_path, command_name)
(its own generated-file header text). Nothing about a catalog's *content* is decided
here; this file only wires the pieces together and writes the manifest.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extractors import _common  # noqa: E402
from extractors import hrldas_noahmp  # noqa: E402
from extractors import mizuroute  # noqa: E402
from extractors import vic  # noqa: E402

PACKS = {
    "hrldas-noahmp": hrldas_noahmp,
    "mizuroute": mizuroute,
    "vic": vic,
}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)

    # --pack must be known before the subcommand choices (which differ per pack) can be
    # built, so resolve it in a lightweight pre-pass; the real parser below re-declares
    # --pack too, purely so `--help` and error messages show it as a documented option.
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--pack", default="hrldas-noahmp", choices=sorted(PACKS))
    pre_args, _ = pre.parse_known_args(argv)
    mod = PACKS[pre_args.pack]

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pack", default="hrldas-noahmp", choices=sorted(PACKS),
                         help="Which pack's extractor module to use (default: hrldas-noahmp)")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in list(mod.CATALOGS) + ["all"]:
        p = sub.add_parser(name)
        p.add_argument("--source-root", required=True, help="Root of the pinned source checkout")
        if name == "all":
            p.add_argument("--out-dir", required=True, help="catalogs/ directory to write into")
        else:
            p.add_argument("--out", required=True, help="Output YAML path (MANIFEST.json under 'all' stays JSON)")
    args = parser.parse_args(argv)

    root = Path(args.source_root).resolve()
    if not root.is_dir():
        sys.exit(f"ERROR: no such source root: {root}")

    if args.command == "all":
        out_dir = Path(args.out_dir)
        written = {}
        for name, func in mod.CATALOGS.items():
            obj = func(root)
            out_path = out_dir / mod.FILENAME[name]
            mod.write_yaml(obj, out_path, name)
            written[mod.FILENAME[name]] = {"count": obj.get("count"), "sha256": _common.sha256_of(out_path)}
            print(f"wrote {out_path} ({obj.get('count')} entries)")
        manifest = {
            "pack": mod.PACK, "generator": "tools/extract_pack.py all",
            "generator_version": mod.GENERATOR_VERSION, "scope": mod.SCOPE,
            "source_commits": mod.SOURCE_COMMITS,
            "files": written,
        }
        # A pack whose only reachable model data lives inside the pinned checkout itself
        # (so there is nothing for validate_catalogs.py to be pointed at from outside)
        # supplies its own deterministic validation report as an optional module hook;
        # a module without one leaves the manifest exactly as before.
        if hasattr(mod, "VALIDATION"):
            manifest["validation"] = mod.VALIDATION(root)
        _common.write_json(manifest, out_dir / "MANIFEST.json")
        print(f"wrote {out_dir / 'MANIFEST.json'}")
        return 0

    obj = mod.CATALOGS[args.command](root)
    mod.write_yaml(obj, Path(args.out), args.command)
    print(f"wrote {args.out} ({obj.get('count')} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
