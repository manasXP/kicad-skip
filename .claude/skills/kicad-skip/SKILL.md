---
name: kicad-skip
description: Programmatically edit KiCad schematic (.kicad_sch) and PCB (.kicad_pcb) files with the kicad-skip Python library, validate with kicad-cli, and enrich with DigiKey/Mouser/JLCPCB data. Use whenever the user wants scripted or batch modification of KiCad files — set/add symbol properties (MPN, LCSC, DNP) across many components, move/clone components, draw wires and labels, query connectivity ("what's connected to U1?"), spatial searches, rename labels, populate BOM fields from distributor APIs, or any "edit my schematic/PCB with Python" request. Also use for the edit→ERC/DRC→export validation loop via kicad-cli. For read-only design review use the `kicad` skill; for distributor searches see `digikey`/`mouser`; for fab prep see `jlcpcb`/`bom`.
---

# kicad-skip: Programmatic KiCad File Editing

[kicad-skip](https://github.com/manasXP/kicad-skip) is an S-expression parser/editor that gives Pythonic, REPL-friendly access to `.kicad_sch` and `.kicad_pcb` files. It is the **editing** counterpart to the read-only `kicad` analysis skill.

## Related Skills

| Skill | Use for |
|---|---|
| `kicad` | Read-only analysis, design review, subcircuit detection, Gerber analysis |
| `bom` | BOM orchestration, property editing conventions, package cross-reference |
| `digikey` / `mouser` | Part search, pricing, stock, datasheet download (prototype sourcing) |
| `lcsc` / `jlcpcb` | LCSC part numbers, JLCPCB BOM/CPL, assembly constraints, ordering |

## Environment

- **Python venv** (kicad-skip 0.2.5 + kicad-sch-api installed):
  `/Users/manaspradhan/Desktop/Design-Studio/KiCAD/.venv/bin/python`
- **kicad-cli** (v10.x): `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`
- If working outside that project, check `python -c "import skip"` and `pip install kicad-skip` if missing.

```bash
VENV=/Users/manaspradhan/Desktop/Design-Studio/KiCAD/.venv/bin/python
KICAD_CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
```

## Helper Script

`scripts/skip_tool.py` covers the common operations without writing ad-hoc code. It **always creates a timestamped `.bak` before writing**.

```bash
$VENV ~/.claude/skills/kicad-skip/scripts/skip_tool.py list board.kicad_sch
$VENV ~/.claude/skills/kicad-skip/scripts/skip_tool.py props board.kicad_sch U1
$VENV ~/.claude/skills/kicad-skip/scripts/skip_tool.py set-prop board.kicad_sch --ref R5 MPN RC0805FR-0710KL
$VENV ~/.claude/skills/kicad-skip/scripts/skip_tool.py set-prop board.kicad_sch --match-ref 'R\d+' Tolerance 1%
$VENV ~/.claude/skills/kicad-skip/scripts/skip_tool.py set-prop board.kicad_sch --match-value '100nF' LCSC C49678
$VENV ~/.claude/skills/kicad-skip/scripts/skip_tool.py connectivity board.kicad_sch U1
$VENV ~/.claude/skills/kicad-skip/scripts/skip_tool.py bom board.kicad_sch          # grouped BOM as JSON
$VENV ~/.claude/skills/kicad-skip/scripts/skip_tool.py erc board.kicad_sch          # kicad-cli ERC + summary
```

For anything beyond these, write inline Python (`$VENV - <<'EOF' ... EOF`) using the API below. Full cheatsheet: `references/api-reference.md`.

## Core API (condensed)

```python
import skip
schem = skip.Schematic('board.kicad_sch')   # prints "can't parsy" warnings — harmless, see Caveats
pcb   = skip.PCB('board.kicad_pcb')

# Symbols — by ref, index, or search
schem.symbol.R14                            # attribute access by reference
schem.symbol.reference_matches(r'(C|R)2[15]')
schem.symbol.value_startswith('10k')

# Properties — Reference, Value, Footprint, Datasheet, MPN, LCSC, ...
sym = schem.symbol.U1
sym.property.Value.value                    # read
sym.property.MPN.value = 'STM32G030F6P6'    # write (only if property exists)
p = sym.property.Datasheet.clone(); p.name = 'LCSC'; p.value = 'C529340'   # create new property

# DNP / BOM flags
sym.dnp.value = True
sym.in_bom.value = False

# Position — ALWAYS move(), it carries child text along (translate() is None in 0.2.5!)
sym.move(127.0, 95.25)                      # absolute (mm)
clone = sym.clone(); clone.move(127.0, 107.95); clone.property.Reference.value = 'R99'

# Wires & labels (these support .new(); other types need .clone())
w = schem.wire.new()
w.start_at(schem.symbol.D1.pin.K); w.end_at([152.4, 101.6])
lbl = schem.label.new(); lbl.value = 'SDA'; lbl.move(140, 100)

# Connectivity (wire-tracing, not full netlist)
sym.attached_wires; sym.attached_labels; sym.attached_symbols; sym.attached_all
schem.symbol.U1.pin.n7.location             # numeric pins prefixed 'n'

# Spatial
schem.symbol.within_circle(150, 100, 25)
schem.within_reach_of(schem.symbol.R1, 10)

# PCB
pcb.footprint.D1.layer = 'B.Cu'
pcb.net.GND; pcb.via[3].move(pcb.footprint.R20.at)

# Save — write to a NEW path or back up first
schem.write('board.kicad_sch')
```

## Caveats (read before editing)

1. **`"Passed key -- can't parsy"` warnings** are kicad-skip not recognizing newer KiCad 9/10 S-expr keys. Unknown keys are preserved on write — safe to ignore. They print during `Schematic()` load AND during `attached_*` traversal, to both stdout and stderr — suppress with `contextlib.redirect_stdout` + `redirect_stderr` around both.
2. **Always assign through `.value`**: `sym.dnp.value = True`. Plain `sym.dnp = True` clobbers the wrapper object.
3. **Back up before in-place `write()`** — copy to `file.YYYYMMDD_HHMMSS.bak` first (the helper script does this automatically). kicad-skip will happily write a file KiCad can't open if you corrupted structure.
4. **Reposition with `move()`**, never by setting `at.value` directly — direct sets leave property text behind. (`translate()` exists in docs but is `None` in v0.2.5 — only `move()` works.)
5. **Only `wire`, `label`, `global_label`, `text` support `.new()`** — create symbols/properties via `.clone()` of an existing one, then edit.
6. **Close the file in KiCad's editor** before writing, or reload it in KiCad afterward (File → Revert) to avoid clobbering.
7. **Connectivity helpers trace wires only** — they don't resolve label-to-label nets or hierarchy. For real net membership, export a netlist with kicad-cli.
8. **`attached_*` throws on power symbols** (`'NoneType' object is not iterable`) — match wire endpoints by coordinate instead.
9. **A pin landing mid-span on a wire does NOT connect** — KiCad only joins at wire endpoints or junctions. After placing a symbol whose pin touches the middle of a wire, add a junction: `j = schem.junction[0].clone(); j.at.value = [x, y]`.
10. **Changing `property.Reference.value` does not update the symbol's `(instances ...)` block**, and ERC/annotation read the instances block. After a kicad-skip reference rename, fix the `(reference "...")` inside `(instances ...)` too (text edit if needed).
11. **Do NOT use kicad-sch-api `.save()` on existing schematics** — it re-resolves embedded `lib_symbols` against the system libraries and silently DELETES definitions it can't find (legacy names like `Device:Q_NMOS_GDS`), corrupting the file. Use kicad-sch-api only for schematics it created. To add a new symbol type to an existing file, inject raw s-expressions instead (see below).

## Adding a New Symbol Type (e.g. PWR_FLAG) to an Existing Schematic

kicad-skip can only `clone()` symbols already present; kicad-sch-api corrupts existing files (caveat 11). The proven recipe is textual injection:

1. Extract the symbol's definition block from the system library (e.g. `(symbol "PWR_FLAG" ...)` from `power.kicad_sym`) via balanced-paren matching; rename to `"power:PWR_FLAG"`; insert it before the closing paren of the schematic's `(lib_symbols ...)` block.
2. Textually clone an existing symbol *instance* block (e.g. a `power:+3V3` placement): swap `lib_id`, shift every `(at x y r)` by the same delta, replace the Reference/Value property values AND the `(reference "...")` in its `(instances ...)` block, and regenerate every UUID with `uuid.uuid4()`.
3. If the pin lands mid-wire, add a junction (caveat 9). Then run ERC.

## Validation Loop (kicad-cli)

After every batch of edits, validate before declaring success:

```bash
KICAD_CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli

# 1. ERC — must not introduce new errors
$KICAD_CLI sch erc board.kicad_sch -o /tmp/erc.json --format json --severity-error
python3 -c "import json;r=json.load(open('/tmp/erc.json'));print(sum(len(s['violations']) for s in r['sheets']),'violations')"

# 2. Visual check — export SVG/PDF and Read it to eyeball placement/wiring
$KICAD_CLI sch export svg board.kicad_sch -o /tmp/sch_svg/
$KICAD_CLI sch export pdf board.kicad_sch -o /tmp/board.pdf

# 3. Netlist / BOM when connectivity or properties changed
$KICAD_CLI sch export netlist board.kicad_sch -o /tmp/board.net
$KICAD_CLI sch export bom board.kicad_sch -o /tmp/bom.csv \
  --fields 'Reference,Value,Footprint,MPN,LCSC,${QUANTITY}' --group-by Value,Footprint

# PCB side
$KICAD_CLI pcb drc board.kicad_pcb -o /tmp/drc.json --format json --severity-error
$KICAD_CLI pcb export gerbers board.kicad_pcb -o /tmp/gerbers/
$KICAD_CLI pcb render board.kicad_pcb -o /tmp/board.png   # 3D render for visual check
```

If ERC/DRC regresses after your edit, restore the `.bak` and retry rather than patching a corrupted file.

## Distributor Enrichment Workflow

The highest-value combo: read the design with kicad-skip → source parts via distributor APIs → write part numbers back as symbol properties → export fab files.

1. **Extract** unique Value+Footprint groups:
   `skip_tool.py bom board.kicad_sch` → JSON groups with refs, value, footprint, existing MPN/LCSC.
2. **Source** each group:
   - DigiKey (primary, prototypes): `digikey` skill — keyword search, pricing, stock, datasheet PDFs. Credentials in `~/.config/secrets.env`.
   - Mouser (secondary): `mouser` skill — when DigiKey lacks stock or for price comparison.
   - LCSC (production / JLCPCB assembly): `lcsc` skill — get `Cxxxxx` numbers, prefer Basic parts (no setup fee per `jlcpcb` skill).
3. **Write back** with `set-prop` (batch by value match):
   ```bash
   $VENV scripts/skip_tool.py set-prop board.kicad_sch --match-value '^100nF$' LCSC C1525
   $VENV scripts/skip_tool.py set-prop board.kicad_sch --ref U1 MPN STM32G030F6P6
   ```
   Property name conventions (match `bom` skill): `MPN`, `Manufacturer`, `LCSC`, `Digikey`, `Mouser`, `Tolerance`.
4. **Verify**: re-run `bom` subcommand; confirm every in-BOM, non-DNP group has an MPN or LCSC number.
5. **Fab export**: hand off to `jlcpcb` skill (BOM/CPL formats, basic-vs-extended parts) or `bom` skill for full orchestration.

## Common Recipes

**Batch-set footprints for all 0805 passives missing one:**
```python
for s in schem.symbol.reference_matches(r'^R\d+'):
    if not s.property.Footprint.value:
        s.property.Footprint.value = 'Resistor_SMD:R_0805_2012Metric'
```

**Find unconnected symbols (quick sanity, not a substitute for ERC):**
```python
for s in schem.symbol:
    ref = s.property.Reference.value
    if not ref.startswith('#') and not s.attached_wires:
        print(ref, 'has no attached wires')
```

**Clone a decoupling cap next to each IC:**
```python
template = schem.symbol.C1
for i, ic in enumerate(schem.symbol.reference_matches(r'^U\d+')):
    c = template.clone()
    c.move(ic.at.value[0] + 7.62, ic.at.value[1])
    c.property.Reference.value = f'C9{i}'
```

**Mark every part with a given value as DNP:**
```python
for s in schem.symbol.value_matches(r'^0R$'):
    s.dnp.value = True
    s.property.Reference.value  # log which ones
```
