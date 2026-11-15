#!/usr/bin/env python3
"""Repair seven unconverted formulas in the existing EPUB (Issue #11).

Run from any directory: python3 tools/repair_epub_math.py [path/to/book.epub]
Uses only Python's standard library. Re-running makes no changes.
The Markdown formulas are correct; these replacements repair the exported XHTML.
"""
from pathlib import Path
from html import escape
import re
import sys
import xml.etree.ElementTree as ET
import zipfile


def frac(numerator, denominator):
    return ('<span class="epub-math-frac">'
            '<span class="epub-math-num">' + numerator + '</span>'
            '<span class="epub-math-den">' + denominator + '</span></span>')


def var(name):
    return '<em>' + name + '</em>'


def probability(event):
    return var('pr') + '(' + event + ')'


a, b, c, w, g, o, n = map(var, ['a', 'b', 'c', 'w', 'g', 'o', 'N'])
given = ' | '
pgo = probability(g + given + o)
png = probability('¬' + g + given + o)
pg, png_prior = probability(g), probability('¬' + g)
REPAIRS = {
    'ch012.xhtml': [
        (r'$\dfrac{\neg(a\land\neg c)}{a\to c}$',
         frac('¬(' + a + ' ∧ ¬' + c + ')', a + ' → ' + c)),
        (r'$1.\ \dfrac{a\to b\quad b\to c}{a\to c}$',
         '1.&#160; ' + frac(a + ' → ' + b + '&#160;&#160;&#160;' + b + ' → ' + c,
                             a + ' → ' + c)),
        (r'$2.\ \dfrac{a\to c}{(a\land b)\to c}$',
         '2.&#160; ' + frac(a + ' → ' + c, '(' + a + ' ∧ ' + b + ') → ' + c)),
    ],
    'ch016.xhtml': [
        (r'$\dfrac{\#w}{N}+\dfrac{\#\neg w}{N}=1$',
         frac('#' + w, n) + ' + ' + frac('#¬' + w, n) + ' = 1'),
    ],
    'ch017.xhtml': [
        (r'$5.\ \dfrac{pr(g|o)}{pr(\neg g|o)} > \dfrac{pr(g)}{pr(\neg g)}$',
         '5.&#160; ' + frac(pgo, png) + ' &gt; ' + frac(pg, png_prior)),
        (r'$\dfrac{pr(g)}{pr(\neg g)} \geq 1$',
         frac(pg, png_prior) + ' ≥ 1'),
        (r'$pr(a|b)=pr(b|a)\times\dfrac{pr(a)}{pr(b)}$',
         probability(a + given + b) + ' = ' + probability(b + given + a)
         + ' × ' + frac(probability(a), probability(b))),
    ],
}
CSS = '''
/* Issue #11: native XHTML fractions, without JavaScript or MathML support. */
.epub-math-display {
  display: block;
  text-align: center;
  margin: 1em 0;
  line-height: 1.4;
}
.epub-math-frac {
  display: inline-block;
  vertical-align: middle;
  text-align: center;
  white-space: nowrap;
  margin: 0 0.15em;
}
.epub-math-num, .epub-math-den {
  display: block;
  padding: 0.08em 0.2em;
}
.epub-math-num { border-bottom: 0.06em solid; }
'''


def repair(path):
    with zipfile.ZipFile(path) as archive:
        entries = [(entry, archive.read(entry.filename)) for entry in archive.infolist()]
    replacements = 0
    output = []
    for entry, data in entries:
        if entry.filename in REPAIRS:
            text = data.decode('utf-8')
            for raw, rendered in REPAIRS[entry.filename]:
                old = '<span class="math inline">' + escape(raw, quote=False) + '</span>'
                new = '<span class="epub-math-display">' + rendered + '</span>'
                if text.count(old) == 1:
                    text = text.replace(old, new)
                    replacements += 1
                elif new not in text:
                    raise ValueError('Unexpected formula content in ' + entry.filename + ': ' + raw)
            data = text.encode('utf-8')
        output.append((entry, data))
    if replacements not in (0, 7):
        raise ValueError('Expected all seven formulas or an already repaired EPUB')
    if not replacements:
        print('Already repaired; no changes.')
        return
    output = [(entry, data + CSS.encode('utf-8') if entry.filename == 'stylesheet.css' else data)
              for entry, data in output]
    # Validate the actual XHTML before replacing the original archive.
    for entry, data in output:
        if entry.filename.endswith('.xhtml'):
            root = ET.fromstring(data)
            for element in root.iter():
                if element.tag.endswith('span') and re.search(r'\\[A-Za-z]+', ''.join(element.itertext())):
                    raise ValueError('Unconverted TeX remains in ' + entry.filename)
    temp = path.with_suffix('.repaired.epub')
    with zipfile.ZipFile(temp, 'w') as archive:
        for entry, data in output:
            archive.writestr(entry, data)
    temp.replace(path)
    print('Repaired seven formulas in chapters 7, 11 and 12.')


if __name__ == '__main__':
    repair(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / 'vsi_logic.epub')
