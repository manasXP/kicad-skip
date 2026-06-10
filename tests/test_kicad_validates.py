'''
External validation gate: KiCAD itself (kicad-cli 10.x) must be able to
parse everything kicad-skip writes. Skipped when kicad-cli is absent.
'''
import skip

from conftest import requires_kicad_cli, run_kicad_cli

pytestmark = requires_kicad_cli


def _netlist(sch_path, out_path):
    res = run_kicad_cli('sch', 'export', 'netlist', '-o', out_path, sch_path)
    assert res.returncode == 0, f'netlist export failed: {res.stderr or res.stdout}'
    return out_path.read_text()


def test_roundtrip_sch_parses_and_netlist_unchanged(sch_copy, tmp_path):
    before = _netlist(sch_copy, tmp_path / 'before.net')
    sch = skip.Schematic(str(sch_copy))
    out = tmp_path / 'roundtrip.kicad_sch'
    sch.write(str(out))
    after = _netlist(out, tmp_path / 'after.net')
    # netlists embed source/date metadata; compare net sections only
    def nets_only(netlist_text):
        idx = netlist_text.find('(nets')
        return netlist_text[idx:] if idx >= 0 else netlist_text
    assert nets_only(before) == nets_only(after), \
        'no-op round-trip changed the extracted netlist'


def test_mutated_sch_parses_and_passes_erc_parse(sch_copy, tmp_path):
    sch = skip.Schematic(str(sch_copy))
    sch.symbol[0].property.Value.value = 'MUTATED'
    lbl = sch.label.new()
    lbl.value = 'TEST_NET2'
    lbl.at.value = [30, 30, 0]
    glbl = sch.global_label.new()
    glbl.value = 'TEST_GLOBAL2'
    glbl.at.value = [40, 40, 0]
    w = sch.wire.new()
    w.start_at([10, 10])
    w.end_at([20, 10])
    j = sch.junction.new()
    j.at.value = [60, 60]
    txt = sch.text.new()
    txt.value = 'mutated by test'
    txt.at.value = [50, 50, 0]
    out = tmp_path / 'mutated.kicad_sch'
    sch.write(str(out))

    # the file must parse: netlist export only succeeds on a valid file
    _netlist(out, tmp_path / 'mutated.net')

    # ERC must run to completion (violations are fine - floating test wire -
    # a parse/format failure is not)
    res = run_kicad_cli('sch', 'erc', '-o', tmp_path / 'erc.rpt', out)
    assert res.returncode == 0, f'ERC could not run: {res.stderr or res.stdout}'
    report = (tmp_path / 'erc.rpt').read_text()
    assert 'ERC report' in report


def test_roundtrip_pcb_parses_and_passes_drc(pcb_copy, tmp_path):
    pcb = skip.PCB(str(pcb_copy))
    out = tmp_path / 'roundtrip.kicad_pcb'
    pcb.write(str(out))
    res = run_kicad_cli('pcb', 'drc', '-o', tmp_path / 'drc.rpt', out)
    assert res.returncode == 0, f'DRC could not run: {res.stderr or res.stdout}'
    report = (tmp_path / 'drc.rpt').read_text()
    assert 'End of Report' in report
