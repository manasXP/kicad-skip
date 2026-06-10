# kicad-skip Full API Reference

Source: https://github.com/manasXP/kicad-skip (fork of psychogenic/kicad-skip), v0.2.5.
Import name is `skip`.

## Loading & Saving

```python
import skip
schem = skip.Schematic('file.kicad_sch')
pcb   = skip.PCB('file.kicad_pcb')

schem.read('other.kicad_sch')   # load another file into this object
schem.reload()                  # re-read last file from disk
schem.write('out.kicad_sch')    # write (any path; in-place allowed)
schem.overwrite()               # write back to the file it was loaded from
```

Loading prints `Passed key <X> -- can't parsy` for unrecognized (KiCad 9/10) keys. The
keys are preserved verbatim on write. Suppress noise:

```python
import contextlib, io, os
with contextlib.redirect_stdout(io.StringIO()):
    schem = skip.Schematic(path)
```

## Schematic Collections

`schem.symbol`, `schem.wire`, `schem.label`, `schem.global_label`, `schem.text`,
`schem.junction`, `schem.no_connect`, `schem.sheet`, `schem.rectangle`,
`schem.polyline`, `schem.image`, `schem.lib_symbols`, `schem.title_block`.

All collections: index access `coll[0]`, iteration, `len()`.

### Symbols

```python
schem.symbol.R14                 # attribute access by reference designator
schem.symbol['R14']              # dict-style
schem.symbol.reference_matches(r'(C|R)2[158]')   # regex on reference
schem.symbol.reference_startswith('R')
schem.symbol.value_matches(r'100[un]')           # regex on Value property
schem.symbol.value_startswith('10k')
```

Symbol attributes:

```python
sym.at                 # ParsedValue [x, y, rotation] (mm)
sym.dnp.value          # bool — do not populate
sym.in_bom.value       # bool
sym.on_board.value     # bool
sym.lib_id.value       # e.g. 'Device:R'
sym.uuid
sym.unit               # multi-unit symbol part
sym.is_power           # True for power:* symbols (#PWR refs)
```

### Properties

```python
for prop in sym.property:
    print(prop.name, '=', prop.value)

sym.property.Reference.value
sym.property.Value.value
sym.property.Footprint.value
sym.property.Datasheet.value
sym.property.MPN.value = 'ABC123'        # only if MPN exists

# Create a new property: clone an existing one
p = sym.property.Datasheet.clone()
p.name = 'LCSC'
p.value = 'C1525'
```

Names with special chars are sanitized for attribute access; names starting with a
digit are prefixed `n` (pin "5" → `pin.n5`). Original names preserved in file.

### Pins

```python
sym.pin.VO          # by name
sym.pin.n5          # pin number 5
sym.pin[0]          # by index
pin.number          # '2'
pin.name
pin.location        # absolute schematic coords (accounts for symbol at/rotation)
```

### Wires

```python
w = schem.wire.new()
w.start_at(schem.symbol.D1.pin.K)    # snap to a pin's location
w.start_at([100, 50])
w.end_at([150, 50])
w.start.value = [100, 50]            # raw coordinate set
w.end.value   = [150, 50]
w.delta_x, w.delta_y                 # computed end - start
w.delta_y = 0                        # force horizontal (moves end)
w.length
```

### Labels / Global Labels / Text

```python
lbl = schem.label.new()              # local net label
lbl.value = 'SDA'
lbl.move(140, 100)

g = schem.global_label.new()
g.value = 'USB_DP'
g.shape.value = 'bidirectional'      # input|output|bidirectional|tri_state|passive

t = schem.text.new()
t.value = 'Power section'
t.move(50, 10)
t.effects.font                       # font sub-attributes

schem.label.value_startswith('VCC')
schem.global_label.value_matches(r'usb_.*')
```

### Junctions / No-connects

`schem.junction[i]`, `schem.no_connect[i]` — have `.at`, support `.clone()`.

### Title Block

```python
schem.title_block.title.value = 'LED Driver Rev B'
schem.title_block.date.value = '2026-06-10'
schem.title_block.company.value
schem.title_block.comment            # numbered comments
```

## Positioning (any element with `at`)

```python
el.at.value = [x, y, rot]   # raw — does NOT move child text; avoid for symbols
el.move(x, y)               # absolute, children follow
el.move(other.at)           # move onto another element
# NOTE: translate() is documented upstream but is None in v0.2.5 — use move() only
```

## Generic Element Operations

```python
el.entity_type      # source s-expr tag, e.g. 'symbol'
el.clone()          # deep copy, appended to parent collection
el.delete()         # remove from document
el.wrap / schem.tree  # raw s-expression access for unsupported constructs
```

Only `wire`, `label`, `global_label`, `text` support `collection.new()`; everything
else is created by `clone()` + edit.

## Connectivity & Spatial Queries

```python
# Wire-graph traversal from a symbol or pin (NOT a netlist — labels don't join nets)
sym.attached_wires
sym.attached_symbols
sym.attached_labels
sym.attached_global_labels
sym.attached_all

# Spatial — on schem itself (all element types) or any positioned collection
schem.within_rectangle(x1, y1, x2, y2)
schem.symbol.within_circle(x, y, radius)
schem.within_reach_of(element, distance)
schem.symbol.between_elements(elA, elB)
```

## PCB Objects

```python
pcb = skip.PCB('board.kicad_pcb')

pcb.footprint.D1
pcb.footprint.D1.layer = 'B.Cu'          # string or pcb.layers.B_Cu
pcb.net.GND; pcb.net['VCC']
pcb.layers.Edge_Cuts; layer.name; layer.type

pcb.segment[0].net / .layer / .start / .end / .width
pcb.via[33].move(pcb.footprint.R20.at)

pcb.gr_text, pcb.gr_line, pcb.gr_rect, pcb.gr_arc
```

PCB support is less complete than schematic support — verify with a DRC +
`kicad-cli pcb render` after edits.

## kicad-cli Quick Reference (v10)

```
kicad-cli sch erc FILE -o out.json --format json [--severity-error]
kicad-cli sch export pdf|svg|netlist|bom|dxf FILE -o OUT
kicad-cli sch export bom FILE -o bom.csv --fields 'Reference,Value,Footprint,MPN,${QUANTITY}' --group-by Value,Footprint
kicad-cli sch export netlist FILE -o out.net [--format kicadsexpr|kicadxml|spice]
kicad-cli sch upgrade FILE

kicad-cli pcb drc FILE -o out.json --format json [--severity-error]
kicad-cli pcb export gerbers|drill|pos|pdf|svg|step|vrml FILE -o OUTDIR
kicad-cli pcb render FILE -o out.png [--side top|bottom] [--zoom N]
kicad-cli pcb upgrade FILE

kicad-cli version
```

Binary: `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`
