'''
Mutation tests: edit/create elements and require the saved output to use
KiCAD 10 structures (quoted uuid strings, (fields_autoplaced yes),
(hide yes) — never the KiCAD 7 bare-symbol forms).
'''
import sexpdata
import skip

from conftest import load_sexp, find_entities


def _save(sch, tmp_path, name='out.kicad_sch'):
    out = tmp_path / name
    sch.write(str(out))
    return load_sexp(out)


def _entity_with_uuid(tree, entity, uuid_value):
    for node in find_entities(tree, entity):
        for u in find_entities(node, 'uuid'):
            if str(u[1]) == uuid_value:
                return node
    return None


def _assert_kicad10_clean(node, what):
    '''No KiCAD-7-era constructs allowed in a freshly created element.'''
    # every uuid value must be a quoted string, not a bare Symbol
    for u in find_entities(node, 'uuid'):
        assert isinstance(u[1], str) and not isinstance(u[1], sexpdata.Symbol), \
            f'{what}: uuid written as bare symbol {u[1]!r}'
    # no bare (fields_autoplaced) — KiCAD 10 writes (fields_autoplaced yes)
    for fa in find_entities(node, 'fields_autoplaced'):
        assert len(fa) > 1, f'{what}: bare (fields_autoplaced) is KiCAD 7 form'
    # no bare `hide` atom — KiCAD 10 writes (hide yes)
    def no_bare_hide(t):
        if isinstance(t, list):
            for el in t[1:]:
                if isinstance(el, sexpdata.Symbol) and str(el) == 'hide':
                    raise AssertionError(f'{what}: bare `hide` is KiCAD 7 form')
                no_bare_hide(el)
    no_bare_hide(node)


def test_set_property_value(sch_copy, tmp_path):
    sch = skip.Schematic(str(sch_copy))
    sym = sch.symbol[0]
    ref = sym.property.Reference.value
    sym.property.Value.value = 'CHANGED_VAL'
    tree = _save(sch, tmp_path)
    props = [p for p in find_entities(tree, 'property') if p[1] == 'Value' and p[2] == 'CHANGED_VAL']
    assert props, f'changed Value property not found in output (symbol {ref})'


def test_clone_symbol(sch_copy, tmp_path):
    sch = skip.Schematic(str(sch_copy))
    src = sch.symbol[0]
    cloned = src.clone()
    cloned.at.value = [200, 200, 0]
    new_uuid = cloned.uuid.value
    assert new_uuid != src.uuid.value, 'clone kept the same uuid'
    tree = _save(sch, tmp_path)
    node = _entity_with_uuid(tree, 'symbol', new_uuid)
    assert node is not None, 'cloned symbol not in output'
    _assert_kicad10_clean(node, 'cloned symbol')


def test_new_wire(sch_copy, tmp_path):
    sch = skip.Schematic(str(sch_copy))
    w = sch.wire.new()
    w.start_at([10, 10])
    w.end_at([20, 10])
    tree = _save(sch, tmp_path)
    node = _entity_with_uuid(tree, 'wire', w.uuid.value)
    assert node is not None, 'new wire not in output'
    _assert_kicad10_clean(node, 'new wire')
    assert find_entities(node, 'stroke'), 'wire missing stroke'


def test_new_label(sch_copy, tmp_path):
    sch = skip.Schematic(str(sch_copy))
    lbl = sch.label.new()
    lbl.value = 'MY_NET'
    lbl.at.value = [30, 30, 0]
    tree = _save(sch, tmp_path)
    node = _entity_with_uuid(tree, 'label', lbl.uuid.value)
    assert node is not None, 'new label not in output'
    assert node[1] == 'MY_NET'
    _assert_kicad10_clean(node, 'new label')


def test_new_global_label(sch_copy, tmp_path):
    sch = skip.Schematic(str(sch_copy))
    glbl = sch.global_label.new()
    glbl.value = 'MY_GLOBAL'
    glbl.at.value = [40, 40, 0]
    tree = _save(sch, tmp_path)
    node = _entity_with_uuid(tree, 'global_label', glbl.uuid.value)
    assert node is not None, 'new global_label not in output'
    _assert_kicad10_clean(node, 'new global_label')
    # KiCAD 10 property structure on the intersheetrefs property
    props = find_entities(node, 'property')
    assert props, 'global_label missing Intersheetrefs property'
    for tok in ('show_name', 'do_not_autoplace'):
        assert find_entities(props[0], tok), \
            f'global_label property missing ({tok} ...) — KiCAD 10 form'


def test_new_text(sch_copy, tmp_path):
    sch = skip.Schematic(str(sch_copy))
    txt = sch.text.new()
    txt.value = 'hello kicad 10'
    txt.at.value = [50, 50, 0]
    tree = _save(sch, tmp_path)
    node = _entity_with_uuid(tree, 'text', txt.uuid.value)
    assert node is not None, 'new text not in output'
    _assert_kicad10_clean(node, 'new text')
    assert find_entities(node, 'exclude_from_sim'), \
        'text missing (exclude_from_sim ...) — KiCAD 10 form'


def test_new_junction(sch_copy, tmp_path):
    sch = skip.Schematic(str(sch_copy))
    j = sch.junction.new()
    j.at.value = [60, 60]
    tree = _save(sch, tmp_path)
    node = _entity_with_uuid(tree, 'junction', j.uuid.value)
    assert node is not None, 'new junction not in output'
    _assert_kicad10_clean(node, 'new junction')
