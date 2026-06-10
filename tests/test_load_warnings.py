'''
Loading a KiCAD 10 schematic must be clean:
 - no "can't parsy" warnings (KiCAD 8+ writes unnamed pins as "" not "~")
 - every lib_symbol pin reachable by number when unnamed
 - no key collisions silently shadowing pins
'''
import logging

import skip


def test_load_emits_no_key_warnings(sch_copy, caplog):
    with caplog.at_level(logging.WARNING):
        skip.Schematic(str(sch_copy))
    bad = [r for r in caplog.records if "can't parsy" in r.getMessage()]
    assert not bad, f'{len(bad)} "can\'t parsy" warnings on load: {bad[0].getMessage()}'


def test_lib_symbol_unnamed_pins_reachable_by_number(sch_copy):
    sch = skip.Schematic(str(sch_copy))
    for libsym in sch.lib_symbols:
        pins = libsym.pin
        named_keys = set(dir(pins))
        for p in pins:
            name = p.name.value
            number = p.number.value
            if name in ('~', ''):
                # unnamed pins must be addressable via their number key (nN)
                assert f'n{number}' in named_keys or number in named_keys, (
                    f'{libsym.value}: unnamed pin {number} not reachable; '
                    f'available: {sorted(named_keys)}'
                )
        # no legacy collision bucket
        assert '_deadbeef' not in named_keys, \
            f'{libsym.value}: pins collapsed into _deadbeef bucket'


def test_lib_symbol_pin_count_matches_collection(sch_copy):
    sch = skip.Schematic(str(sch_copy))
    for libsym in sch.lib_symbols:
        raw_count = 0
        for unit in libsym.symbol:
            raw_count += len(unit.getElementsByEntityType('pin'))
        assert len(libsym.pin) == raw_count, (
            f'{libsym.value}: collection has {len(libsym.pin)} pins, '
            f'file has {raw_count}'
        )
