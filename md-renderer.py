#!/usr/bin/env python

import sys
import unicodedata

import misaka as m
import houdini as h
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

formatter = HtmlFormatter(style='friendly')


# Create a custom renderer
class HighlightingRenderer(m.HtmlRenderer):
    def block_code(self, text, lang):
        text = m.smartypants(text)

        output = ''

        if not lang:
            return '\n<pre><code>%s</code></pre>\n' % \
                h.escape_html(text.strip())

        try:
            lexer = get_lexer_by_name(lang, stripall=True)
        except:
            output += '<b>Language "' + lang + '" not supported</b>'
            lexer = get_lexer_by_name(text, stripall=True)

        output += highlight(text, lexer, formatter)

        return output

# And use the renderer
renderer = HighlightingRenderer(flags=m.HTML_HARD_WRAP | m.HTML_USE_XHTML)

md = m.Markdown(renderer,
                extensions=m.EXT_FENCED_CODE | m.EXT_NO_INTRA_EMPHASIS |
                m.EXT_TABLES | m.EXT_NO_INTRA_EMPHASIS | m.EXT_AUTOLINK |
                m.EXT_STRIKETHROUGH | m.EXT_SUPERSCRIPT)

with open(sys.argv[1], 'r') as fp:
    file_contents = fp.read()
    file_contents = unicodedata.normalize('NFKD', file_contents)

    print(('<style>\n' + formatter.get_style_defs() + '</style>'))

    print((md(file_contents)))
