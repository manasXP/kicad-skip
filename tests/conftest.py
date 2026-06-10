'''
Shared fixtures and helpers for the kicad-skip test suite.

All comparisons of KiCAD files are SEMANTIC (s-expression tree equality),
never textual: kicad-skip's writer formats output differently than KiCAD's
own pretty-printer, so byte/line diffs are meaningless.
'''
import math
import shutil
import subprocess
from pathlib import Path

import pytest
import sexpdata

FIXTURES = Path(__file__).parent / 'fixtures'
SCH_FIXTURE = FIXTURES / 'led_array_v10.kicad_sch'
PCB_FIXTURE = FIXTURES / 'minimal_v10.kicad_pcb'

KICAD_CLI = Path('/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')

requires_kicad_cli = pytest.mark.skipif(
    not KICAD_CLI.exists(), reason='kicad-cli not installed'
)


@pytest.fixture
def sch_copy(tmp_path):
    '''A throwaway copy of the KiCAD 10 schematic fixture.'''
    dest = tmp_path / SCH_FIXTURE.name
    shutil.copy(SCH_FIXTURE, dest)
    return dest


@pytest.fixture
def pcb_copy(tmp_path):
    '''A throwaway copy of the KiCAD 10 PCB fixture.'''
    dest = tmp_path / PCB_FIXTURE.name
    shutil.copy(PCB_FIXTURE, dest)
    return dest


def load_sexp(path):
    with open(path) as f:
        return sexpdata.loads(f.read())


def _atom_key(a):
    '''Normalize an s-expression atom for semantic comparison.

    - numbers compare numerically (0 == 0.0)
    - Symbol vs str compare by their string value: KiCAD's parser does not
      distinguish a bare token from a quoted one for the values we compare.
    '''
    if isinstance(a, bool):
        return ('b', a)
    if isinstance(a, (int, float)):
        return ('n', float(a))
    if isinstance(a, sexpdata.Symbol):
        return ('s', str(a))
    return ('s', str(a))


def sexp_equal(a, b, path='/'):
    '''Recursive semantic equality of two parsed s-expression trees.

    Returns (True, None) or (False, "description of first difference").
    '''
    a_is_list = isinstance(a, list)
    b_is_list = isinstance(b, list)
    if a_is_list != b_is_list:
        return False, f'{path}: list vs atom ({a!r} vs {b!r})'
    if not a_is_list:
        ka, kb = _atom_key(a), _atom_key(b)
        if ka[0] == 'n' and kb[0] == 'n':
            if not math.isclose(ka[1], kb[1], rel_tol=1e-9, abs_tol=1e-9):
                return False, f'{path}: {a!r} != {b!r}'
            return True, None
        if ka != kb:
            return False, f'{path}: {a!r} != {b!r}'
        return True, None
    if len(a) != len(b):
        tag = str(a[0]) if a and not isinstance(a[0], list) else '?'
        return False, f'{path}({tag}): length {len(a)} != {len(b)}'
    for i, (ea, eb) in enumerate(zip(a, b)):
        tag = str(a[0]) if a and not isinstance(a[0], list) else '?'
        ok, why = sexp_equal(ea, eb, f'{path}{tag}[{i}]/')
        if not ok:
            return False, why
    return True, None


def count_entities(tree, name):
    '''Count nodes anywhere in the tree whose head symbol is `name`.'''
    n = 0
    if isinstance(tree, list):
        if tree and isinstance(tree[0], sexpdata.Symbol) and str(tree[0]) == name:
            n += 1
        for el in tree:
            n += count_entities(el, name)
    return n


def find_entities(tree, name):
    '''Collect nodes anywhere in the tree whose head symbol is `name`.'''
    found = []
    if isinstance(tree, list):
        if tree and isinstance(tree[0], sexpdata.Symbol) and str(tree[0]) == name:
            found.append(tree)
        for el in tree:
            found.extend(find_entities(el, name))
    return found


def run_kicad_cli(*args):
    return subprocess.run(
        [str(KICAD_CLI), *[str(a) for a in args]],
        capture_output=True, text=True, timeout=120,
    )
