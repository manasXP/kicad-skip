'''
No-op round-trip: load a KiCAD 10 file, save it unchanged, and require
semantic equality of the s-expression trees plus preservation of the
format version header and newer (KiCAD 8/9/10) tokens.
'''
import skip

from conftest import (
    load_sexp, sexp_equal, count_entities, find_entities,
)


def _roundtrip(src_path, out_path, klass):
    doc = klass(str(src_path))
    doc.write(str(out_path))
    return load_sexp(src_path), load_sexp(out_path)


def test_sch_roundtrip_semantic_equality(sch_copy, tmp_path):
    out = tmp_path / 'out.kicad_sch'
    before, after = _roundtrip(sch_copy, out, skip.Schematic)
    ok, why = sexp_equal(before, after)
    assert ok, f'round-trip changed the tree: {why}'


def test_sch_roundtrip_preserves_version_header(sch_copy, tmp_path):
    out = tmp_path / 'out.kicad_sch'
    before, after = _roundtrip(sch_copy, out, skip.Schematic)
    assert find_entities(after, 'version')[0][1] == find_entities(before, 'version')[0][1]
    assert find_entities(after, 'generator_version'), 'generator_version dropped'


def test_sch_roundtrip_preserves_new_tokens_and_counts(sch_copy, tmp_path):
    out = tmp_path / 'out.kicad_sch'
    before, after = _roundtrip(sch_copy, out, skip.Schematic)
    for token in ('exclude_from_sim', 'embedded_fonts', 'in_pos_files',
                  'show_name', 'do_not_autoplace', 'sheet_instances',
                  'symbol', 'property', 'pin', 'wire', 'junction', 'label'):
        assert count_entities(after, token) == count_entities(before, token), \
            f'count of ({token} ...) changed across round-trip'


def test_pcb_roundtrip_semantic_equality(pcb_copy, tmp_path):
    out = tmp_path / 'out.kicad_pcb'
    before, after = _roundtrip(pcb_copy, out, skip.PCB)
    ok, why = sexp_equal(before, after)
    assert ok, f'round-trip changed the tree: {why}'


def test_pcb_roundtrip_preserves_counts(pcb_copy, tmp_path):
    out = tmp_path / 'out.kicad_pcb'
    before, after = _roundtrip(pcb_copy, out, skip.PCB)
    for token in ('footprint', 'pad', 'segment', 'gr_line', 'net', 'layers'):
        assert count_entities(after, token) == count_entities(before, token), \
            f'count of ({token} ...) changed across round-trip'
