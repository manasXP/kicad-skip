'''
SymbolPin.location must agree with KiCAD's own connectivity.

Ground truth derived from kicad-cli netlist export of the fixture:
  - D1 (Device:LED at 41.42,81.43 rot 270): A(2) connects to the GND row
    BELOW the symbol -> (41.42, 85.24); K(1) above -> (41.42, 77.62)
  - D7 (Device:D at 187.96,185.42 rot 270): K(1) connects to the +12V
    junction ABOVE -> (187.96, 181.61)
  - R1 (Device:R at 41.42,62.38 rot 0): 1 -> (41.42, 58.57), 2 -> (41.42, 66.19)

Regression for the v0.2.5 bug where AtValue.rotate90degrees() stepped
clockwise instead of counterclockwise, mirroring pin positions for symbols
rotated 90/270 degrees.
'''
import pytest
import skip
from skip.at_location import AtValue

from conftest import SCH_FIXTURE


@pytest.fixture(scope='module')
def sch():
    return skip.Schematic(str(SCH_FIXTURE))


def pin_xy(sym, number):
    for p in sym.pin:
        if str(p.number) == number:
            loc = p.location
            return (loc.x, loc.y)
    raise AssertionError(f'no pin {number}')


def test_rot0_pin_locations(sch):
    r1 = sch.symbol.R1
    assert pin_xy(r1, '1') == (41.42, 58.57)
    assert pin_xy(r1, '2') == (41.42, 66.19)


def test_rot270_led_pin_locations(sch):
    d1 = sch.symbol.D1
    assert pin_xy(d1, '1') == (41.42, 77.62), 'K must be above center at rot 270'
    assert pin_xy(d1, '2') == (41.42, 85.24), 'A must be below center at rot 270'


def test_rot270_diode_pin_locations(sch):
    d7 = sch.symbol.D7
    assert pin_xy(d7, '1') == (187.96, 181.61), 'K must be above center at rot 270'
    assert pin_xy(d7, '2') == (187.96, 189.23), 'A must be below center at rot 270'


def test_atvalue_rotate90_is_counterclockwise():
    # one CCW step in the library's y-up frame: (x, y) -> (-y, x)
    at = AtValue([3.81, 0, 0])
    at.rotate90degrees()
    assert (at.x, at.y, at.rotation) == (0, 3.81, 90)
    at.rotate90degrees()
    assert (at.x, at.y, at.rotation) == (-3.81, 0, 180)
    at.rotate90degrees()
    assert (at.x, at.y, at.rotation) == (0, -3.81, 270)
    at.rotate90degrees()
    assert (at.x, at.y, at.rotation) == (3.81, 0, 0)
