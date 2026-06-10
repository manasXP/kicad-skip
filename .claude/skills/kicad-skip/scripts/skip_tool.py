#!/usr/bin/env python3
"""skip_tool.py — common kicad-skip operations on .kicad_sch files.

Subcommands:
  list <file>                          List symbols (ref, value, footprint, MPN, LCSC, DNP)
  props <file> <ref>                   Show all properties of one symbol
  set-prop <file> (--ref R5 | --match-ref RX | --match-value RX) NAME VALUE
                                       Set (or create) a property on matching symbols
  connectivity <file> <ref>            Wires/labels/symbols attached to a symbol
  bom <file>                           Grouped BOM (Value+Footprint) as JSON
  erc <file>                           Run kicad-cli ERC, print summary

Writes are preceded by a timestamped backup: <file>.YYYYMMDD_HHMMSS.bak
"""
import argparse
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

KICAD_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"


def load_schematic(path):
    import skip
    # suppress "Passed key -- can't parsy" noise from unrecognized KiCad 9/10 keys
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return skip.Schematic(path)


def backup(path):
    bak = f"{path}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
    shutil.copy2(path, bak)
    return bak


def prop_key(name):
    # kicad-skip cleanses property names for attribute access ("BOM Comments"
    # -> "BOM_Comments"); compare in that normalized space so lookups match
    # regardless of which form the caller uses
    return re.sub(r"[^\w\d_]", "_", name)


def prop_value(sym, name):
    for p in sym.property:
        if prop_key(p.name) == prop_key(name):
            return p.value
    return None


def sym_ref(sym):
    return prop_value(sym, "Reference") or "?"


def real_symbols(schem):
    return [s for s in schem.symbol if not sym_ref(s).startswith("#")]


def find_symbol(schem, ref):
    for s in schem.symbol:
        if sym_ref(s) == ref:
            return s
    sys.exit(f"error: no symbol with reference {ref!r}")


def cmd_list(args):
    schem = load_schematic(args.file)
    rows = []
    for s in real_symbols(schem):
        rows.append({
            "ref": sym_ref(s),
            "value": prop_value(s, "Value"),
            "footprint": prop_value(s, "Footprint") or "",
            "mpn": prop_value(s, "MPN") or "",
            "lcsc": prop_value(s, "LCSC") or "",
            "dnp": bool(s.dnp.value),
        })
    rows.sort(key=lambda r: (re.sub(r"\d+$", "", r["ref"]), int(re.sub(r"\D", "", r["ref"]) or 0)))
    w = max((len(r["ref"]) for r in rows), default=3)
    for r in rows:
        flags = " DNP" if r["dnp"] else ""
        print(f"{r['ref']:<{w}}  {r['value'] or '':<16} {r['footprint']:<40} MPN={r['mpn'] or '-'} LCSC={r['lcsc'] or '-'}{flags}")
    print(f"\n{len(rows)} symbols")


def cmd_props(args):
    schem = load_schematic(args.file)
    s = find_symbol(schem, args.ref)
    print(f"{args.ref}  lib_id={s.lib_id.value}  at={list(s.at.value)}  dnp={bool(s.dnp.value)}  in_bom={bool(s.in_bom.value)}")
    for p in s.property:
        print(f"  {p.name} = {p.value!r}")


def cmd_set_prop(args):
    schem = load_schematic(args.file)
    if args.ref:
        targets = [find_symbol(schem, args.ref)]
    elif args.match_ref:
        targets = [s for s in real_symbols(schem) if re.search(args.match_ref, sym_ref(s))]
    else:
        targets = [s for s in real_symbols(schem)
                   if re.search(args.match_value, prop_value(s, "Value") or "")]
    if not targets:
        sys.exit("error: no symbols matched")

    for s in targets:
        existing = next((p for p in s.property if prop_key(p.name) == prop_key(args.name)), None)
        if existing is not None:
            existing.value = args.value
        else:
            # clone a normally-hidden property so the new field isn't drawn on canvas
            template = next((p for p in s.property if p.name == "Datasheet"), s.property[len(s.property) - 1])
            p = template.clone()
            p.name = args.name
            p.value = args.value
        print(f"{sym_ref(s)}: {args.name} = {args.value}")

    if args.dry_run:
        print("(dry run — not written)")
        return
    bak = backup(args.file)
    schem.write(args.file)
    print(f"wrote {args.file} (backup: {bak})")


def cmd_connectivity(args):
    schem = load_schematic(args.file)
    s = find_symbol(schem, args.ref)
    # traversal re-parses elements and re-emits "can't parsy" noise — suppress it
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        wires, labels, glabels, symbols = (
            s.attached_wires, s.attached_labels, s.attached_global_labels, s.attached_symbols)
    print(f"{args.ref} ({prop_value(s, 'Value')})")
    print(f"  attached wires: {len(wires)}")
    for lbl in labels:
        print(f"  label: {lbl.value}")
    for g in glabels:
        print(f"  global label: {g.value}")
    for other in symbols:
        print(f"  symbol: {sym_ref(other)} ({prop_value(other, 'Value')})")
    print("note: wire-tracing only; label-joined nets need a kicad-cli netlist export")


def cmd_bom(args):
    schem = load_schematic(args.file)
    groups = {}
    for s in real_symbols(schem):
        if not s.in_bom.value or s.dnp.value:
            continue
        key = (prop_value(s, "Value") or "", prop_value(s, "Footprint") or "")
        g = groups.setdefault(key, {
            "value": key[0], "footprint": key[1], "refs": [],
            "mpn": prop_value(s, "MPN") or "", "lcsc": prop_value(s, "LCSC") or "",
        })
        g["refs"].append(sym_ref(s))
    out = sorted(groups.values(), key=lambda g: g["refs"][0])
    for g in out:
        g["qty"] = len(g["refs"])
    print(json.dumps(out, indent=2))


def cmd_erc(args):
    out = os.path.join(tempfile.mkdtemp(), "erc.json")
    r = subprocess.run([KICAD_CLI, "sch", "erc", args.file, "-o", out,
                        "--format", "json", "--exit-code-violations"],
                       capture_output=True, text=True)
    if not os.path.exists(out):
        sys.exit(f"ERC failed to run:\n{r.stdout}{r.stderr}")
    report = json.load(open(out))
    n_err = n_warn = 0
    for sheet in report.get("sheets", []):
        for v in sheet.get("violations", []):
            sev = v.get("severity", "?")
            if sev == "error":
                n_err += 1
            else:
                n_warn += 1
            pos = v.get("items", [{}])[0].get("pos", {})
            print(f"[{sev}] {v.get('type')}: {v.get('description')} @ ({pos.get('x')}, {pos.get('y')})")
    print(f"\n{n_err} errors, {n_warn} warnings (full report: {out})")
    sys.exit(1 if n_err else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list");  p.add_argument("file"); p.set_defaults(fn=cmd_list)
    p = sub.add_parser("props"); p.add_argument("file"); p.add_argument("ref"); p.set_defaults(fn=cmd_props)

    p = sub.add_parser("set-prop")
    p.add_argument("file")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--ref")
    g.add_argument("--match-ref", metavar="REGEX")
    g.add_argument("--match-value", metavar="REGEX")
    p.add_argument("name")
    p.add_argument("value")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_set_prop)

    p = sub.add_parser("connectivity"); p.add_argument("file"); p.add_argument("ref"); p.set_defaults(fn=cmd_connectivity)
    p = sub.add_parser("bom"); p.add_argument("file"); p.set_defaults(fn=cmd_bom)
    p = sub.add_parser("erc"); p.add_argument("file"); p.set_defaults(fn=cmd_erc)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
