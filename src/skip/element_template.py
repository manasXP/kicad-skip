'''
Created on Feb 5, 2024

@author: Pat Deegan
@copyright: Copyright (C) 2024 Pat Deegan, https://psychogenic.com

Templates mirror the structures KiCAD 10 (schematic format 20260306)
writes itself, as produced by `kicad-cli sch upgrade`:
  - uuid values are quoted strings (not bare symbols)
  - (fields_autoplaced yes) / (hide yes) -- never the bare KiCAD 7 forms
  - text carries (exclude_from_sim no)
  - global_label Intersheetrefs property carries (show_name no) and
    (do_not_autoplace no)
The placeholder uuid strings are replaced with fresh uuid4 values by
collection new().
'''

from sexpdata import Symbol
ElementTemplate = {

    'wire': [Symbol('wire'), [Symbol('pts'), [Symbol('xy'), 0,0], [Symbol('xy'), 0, 2.54]],
             [Symbol('stroke'), [Symbol('width'), 0], [Symbol('type'), Symbol('default')]],
             [Symbol('uuid'), 'a3a399fe-0000-0000-0000-000000000000']],

    'global_label': [Symbol('global_label'), 'GLABEL', [Symbol('shape'), Symbol('input')],
                     [Symbol('at'), 27.94, 33.02, 180], [Symbol('fields_autoplaced'), Symbol('yes')],
                     [Symbol('effects'), [Symbol('font'), [Symbol('size'), 1.27, 1.27]],
                      [Symbol('justify'), Symbol('right')]],
                     [Symbol('uuid'), 'a3a399fe-0000-0000-0000-000000000001'],
                     [Symbol('property'), 'Intersheetrefs', '${INTERSHEET_REFS}',
                      [Symbol('at'), 21.6891, 33.02, 0],
                      [Symbol('hide'), Symbol('yes')],
                      [Symbol('show_name'), Symbol('no')],
                      [Symbol('do_not_autoplace'), Symbol('no')],
                      [Symbol('effects'),
                    [Symbol('font'), [Symbol('size'), 1.27, 1.27]],
                    [Symbol('justify'), Symbol('right')]]]],

    'label': [Symbol('label'), 'LABEL',
              [Symbol('at'), 25.4, 25.4, 0],
              [Symbol('effects'), [Symbol('font'), [Symbol('size'), 1.27, 1.27]],
               [Symbol('justify'), Symbol('left'), Symbol('bottom')]],
              [Symbol('uuid'), 'a3a399fe-0000-0000-0000-000000000002']],


    'text': [Symbol('text'), 'hello',
             [Symbol('exclude_from_sim'), Symbol('no')],
             [Symbol('at'), 58.42, 48.26, 0],
             [Symbol('effects'), [Symbol('font'), [Symbol('size'), 1.27, 1.27]],
            [Symbol('justify'), Symbol('left'), Symbol('bottom')]],
             [Symbol('uuid'), 'a3a399fe-0000-0000-0000-000000000003']],


    'junction': [Symbol('junction'), [Symbol('at'), 50.8, 38.1], [Symbol('diameter'), 0],
                 [Symbol('color'), 0, 0, 0, 0],
                 [Symbol('uuid'), 'a3a399fe-0000-0000-0000-000000000004']]
}
