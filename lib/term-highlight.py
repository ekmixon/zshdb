#!/usr/bin/env python
# -*- coding: utf-8 -*-
#   Copyright (C) 2016, 2019 Rocky Bernstein <rocky@gnu.org>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

# A lot of this comes from my Python trepan debugger "format" module.
'''Pygments-related terminal formatting'''

from __future__ import print_function

import warnings
import os, re, sys

from tempfile import mktemp
from pygments import highlight
from pygments.console    import ansiformat
from pygments.lexers     import BashLexer, RstLexer
from pygments.filter     import Filter
from pygments.formatter  import Formatter
from pygments.formatters.terminal import TERMINAL_COLORS
from pygments.formatters import TerminalFormatter, Terminal256Formatter
from pygments.token      import Keyword, Name, Comment, String, Error, \
    Number, Operator, Generic, Token, Whitespace
from pygments.util       import get_choice_opt

from pygments.styles import get_all_styles
style_names = sorted(list(get_all_styles()))

warnings.simplefilter("ignore")

# FIXME: change some horrible colors under atom dark
# this is a hack until I get general way to do colorstyle setting
color_scheme = TERMINAL_COLORS.copy()
color_scheme[Generic.Strong] = ('*black*', '*white*')
color_scheme[Name.Variable]  = ('_black_', '_white_')

color_scheme[Generic.Strong] = ('*black*', '*white*')
color_scheme[Name.Variable]  = ('_black_', '_white_')
color_scheme[Generic.Emph]   = color_scheme[Comment.Preproc]

# FIXME: change some horrible colors under atom dark
# this is a hack until I get general way to do colorstyle setting
color_scheme[Token.Comment]  = ('darkgray', 'white')
color_scheme[Token.Keyword]  = ('darkblue', 'turquoise')
color_scheme[Token.Number]  = ('darkblue', 'turquoise')
color_scheme[Keyword]  = ('darkblue', 'turquoise')
color_scheme[Number]  = ('darkblue', 'turquoise')

def format_token(ttype, token, colorscheme=color_scheme,
                 highlight='light' ):
    if highlight == 'plain': return token
    dark_bg = highlight == 'dark'

    if color := colorscheme.get(ttype):
        color = color[dark_bg]
        return ansiformat(color, token)
    return token

Arrow      = Name.Variable
Compare    = Name.Exception
Const      = String
Filename   = Comment.Preproc
Function   = Name.Function
Label      = Operator.Word
LineNumber = Number
Offset     = Operator
Opcode     = Name.Function
Return     = Operator.Word
Var        = Keyword
Verbatim   = String

# Should come last since "Name" is used above
Name = Comment.Preproc


class RstFilter(Filter):

    def __init__(self, **options):
        Filter.__init__(self, **options)

    def filter(self, lexer, stream):
        last_was_heading_title = ''
        for ttype, value in stream:
            if ttype is Token.Name.Variable:
                value = value[1:-1]
                last_was_heading_title  = ''
            if ttype is Token.Generic.Emph:
                value = value[1:-1]
                last_was_heading_title  = ''
            elif ttype is Token.Generic.Strong:
                value = value[2:-2]
                last_was_heading_title = ''
            elif ttype is Token.Text and last_was_heading_title \
                  and value == "\n":
                value = ''
            elif ttype is Token.Generic.Heading:
                # Remove the underline line following a section header
                # That is remove:
                # Header
                # ------ <- remove this line
                if last_was_heading_title and \
                      re.match(r'^(?:[=]|[-])+$', value):
                    value = ''
                    last_was_heading_title = ''
                else:
                    # We store the entire string in case someday we want to
                    # match whether the underline size matches the title size
                    last_was_heading_title  = value
            yield ttype, value
        return
    pass


class RSTTerminalFormatter(Formatter):
    r"""
    Format tokens with ANSI color sequences, for output in a text console.
    Color sequences are terminated at newlines, so that paging the output
    works correctly.

    The `get_style_defs()` method doesn't do anything special since there is
    no support for common styles.

    Options accepted:

    `bg`
        Set to ``"light"`` or ``"dark"`` depending on the terminal's background
        (default: ``"light"``).

    `colorscheme`
        A dictionary mapping token types to (lightbg, darkbg) color names or
        ``None`` (default: ``None`` = use builtin colorscheme).
    """
    name = 'Terminal'
    aliases = ['terminal', 'console']
    filenames = []

    def __init__(self, **options):
        Formatter.__init__(self, **options)
        self.darkbg = get_choice_opt(options, 'bg',
                                     ['light', 'dark'], 'light') != 'dark'
        self.colorscheme = options.get('colorscheme', None) or color_scheme
        self.width = options.get('width', 80)
        self.verbatim = False
        self.in_list  = False
        self.column   = 1
        self.last_was_nl = False
        return

    def reset(self, width=None):
        self.column = 0
        if width: self.width = width
        return

    def format(self, tokensource, outfile):
        # hack: if the output is a terminal and has an encoding set,
        # use that to avoid unicode encode problems
        if not self.encoding and hasattr(outfile, "encoding") and \
               hasattr(outfile, "isatty") and outfile.isatty() and \
               sys.version_info < (3,):
            self.encoding = outfile.encoding
        self.outfile = outfile
        return Formatter.format(self, tokensource, outfile)

    def write_verbatim(self, text):
        # If we are doing color, then change to the verbatim
        # color
        if self.__class__ != MonoRSTTerminalFormatter:
            cs = self.colorscheme.get(Verbatim)
            color = cs[self.darkbg]
        else:
            color = None
        return self.write(text, color)

    def write(self, text, color):
        color_text = text
        if color: color_text = ansiformat(color, color_text)
        self.outfile.write(color_text)
        self.column += len(text)
        return self.column

    def write_nl(self):
        self.outfile.write('\n')
        self.column = 0
        return self.column

    def reflow_text(self, text, color):
        # print '%r' % text
        # from trepan.api import debug
        # if u' or ' == text: debug()
        last_last_nl = self.last_was_nl
        if text == '':
            pass
        elif text[-1] == '\n':
            if self.last_was_nl:
                self.write_nl()
                self.write_nl()
                text = text[:-1]
            elif self.verbatim:
                self.write_verbatim(text)
                self.column = 0
                self.verbatim = False
                self.last_was_nl = True
                return
            else:
                self.write(' ', color)
                text = text[:-1]
            self.last_was_nl = True
            if text == '': return
            while text[-1] == '\n':
                self.write_nl()
                text = text[:-1]
                if text == '': return
        else:
            self.last_was_nl = False
        self.in_list = False
        if last_last_nl:
            if text[:3] == ' * ': self.in_list = True
            elif text[:2] == '  ': self.verbatim = True
        # FIXME: there may be nested lists, tables and so on.
        if self.verbatim:
            self.write_verbatim(text)
        elif self.in_list:
            # FIXME:
            self.write(text, color,)
        else:
            words = re.compile('[ \t]+').split(text)
            for word in words[:-1]:
                # print "column: %d, word %s" % (self.column, word)
                if (self.column + len(word) + 1) >= self.width:
                    self.write_nl()
                if self.column != 0 or word != '':
                    self.write(f'{word} ', color)
            if words[-1]:
                # print "column2: %d, word %r" % (self.column, words[-1])
                if (self.column + len(words[-1])) >= self.width:
                    self.write_nl()
                self.write(words[-1], color)
        return

    def format_unencoded(self, tokensource, outfile):
        for ttype, text in tokensource:
            color = self.colorscheme.get(ttype)
            while color is None:
                ttype = ttype[:-1]
                color = self.colorscheme.get(ttype)
            if color: color = color[self.darkbg]
            self.reflow_text(text, color)
        return
    pass


class MonoRSTTerminalFormatter(RSTTerminalFormatter):
    def format_unencoded(self, tokensource, outfile):
        for ttype, text in tokensource:
            if ttype is Token.Name.Variable:
                text = '"%s"' % text
            elif ttype is Token.Generic.Emph:
                text = f"*{text}*"
            elif ttype is Token.Generic.Strong:
                text = text.upper()
            self.reflow_text(text, None)
        return
    pass


class MonoTerminalFormatter(TerminalFormatter):
    def format_unencoded(self, tokensource, outfile):
        for ttype, text in tokensource:
            if ttype is Token.Name.Variable:
                text = '"%s"' % text
            elif ttype is Token.Generic.Emph:
                type
                text = f"*{text}*"
            elif ttype is Token.Generic.Strong:
                text = text.upper()
            outfile.write(text)
        return
    pass

rst_lex = RstLexer()
rst_filt = RstFilter()
rst_lex.add_filter(rst_filt)
color_tf = RSTTerminalFormatter(colorscheme=color_scheme)
mono_tf  = MonoRSTTerminalFormatter()


def rst_text(text, mono, width=80):
    tf = mono_tf if mono else color_tf
    tf.reset(width)
    return highlight(text, rst_lex, tf)

def syntax_highlight_file(input_filename, to_stdout=False, bg='light',
                          colors_file=None, style=None):
    if to_stdout:
        outfile = sys.stdout
        out_filename = None
    else:
        basename = os.path.basename(input_filename)
        out_filename = mktemp('.term', f'{basename}_')
        try:
            outfile = open(out_filename, 'w')
        except:
            print(f"Unexpected error in opening output file {out_filename}")
            sys.exit(1)
    if input_filename:
        if not os.path.exists(input_filename):
            sys.stderr.write("input file %s doesn't exist\n" % input_filename)
            sys.exit(2)
        try:
            infile = open(input_filename)
        except:
            print(f"Unexpected error in opening input file {input_filename}")
            sys.exit(2)
    else:
        infile = sys.stdin
    if style:
        formatter = Terminal256Formatter(bg=bg, style=style)
    else:
        formatter = TerminalFormatter(bg=bg)
        formatter.colorscheme = TERMINAL_COLORS

    if colors_file is not None and os.path.isfile(colors_file):
        try:
            with open(colors_file) as f:
                code = compile(f.read(), colors_file, 'exec')
                exec(code)
        except:
            sys.exit(10)
    for code_line in infile.readlines():
        line = highlight(code_line, BashLexer(), formatter).strip("\r\n")
        outfile.write(line + "\n")
    outfile.close
    if out_filename:
        print(out_filename)
    sys.exit(0)

def print_rst_file(input_filename, tf, width, to_stdout=False, bg='light',
                        colors_file=None, style=None):
    if input_filename:
        if not os.path.exists(input_filename):
            sys.stderr.write("input file %s doesn't exist\n" % input_filename)
            sys.exit(2)
        try:
            infile = open(input_filename)
        except:
            print(f"Unexpected error in opening input file {input_filename}")
            sys.exit(2)
    else:
        infile = sys.stdin
    string = infile.read()
    tf.reset(width)
    print(highlight(string, rst_lex, tf))

program = os.path.basename(__file__)
def usage():
    sys.stderr.write("""usage:
%s [FILE | --tty]  [--bg {dark|light}] [color-file | --style *pygments-style-name*]]
%s [--help | -h | --version | -V

Runs pygmentize to prettyprint a file for terminal output
""" % (program, program))
    sys.exit(2)

def version():
    sys.stderr.write("%s version 1.0\n" % program)


from getopt import getopt, GetoptError
def main():
    try:
        opts, args = getopt(sys.argv[1:], "RLTVhb:c:S:w:",
                            ['rst', "list-styles", "tty", "help", "version",
                             "bg=", "colors=", 'style=', 'width='])
    except GetoptError as err:
        # print help information and exit:
        print(err)
        usage()
    dark_light = 'light'
    colors_file = None
    style_name = None
    to_stdout = False
    format_to_rst = False
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        if o in ("-V", "--version"):
            version()
            sys.exit()
        elif o in ("-b", "--bg"):
            if a in ['dark', 'light']:
                dark_light = a
            else:
                assert False, "expecting 'dark' or 'light'; got %s" % a
        elif o in ("-c", "--colors"):
            colors_file = a
        elif o in ("-L", "--list-styles"):
            print(' '.join(style_names))
            sys.exit()
        elif o in ("-R", "--rst"):
            format_to_rst = True
        elif o in ("-S", "--style"):
            if a not in style_names:
                sys.stderr.write(f'style name {a} not found. Valid style names are: ')
                sys.stderr.write(', '.join(style_names))
                sys.exit(1)
            style_name = a
        elif o in ("-T", '--tty'):
            to_stdout = True
        elif o in ("-w", "--width"):
            width = int(a)
        else:
            assert False, f"unhandled option {o}"
    if len(args) == 0:
        to_stdout = True
        filename = None
    elif len(args) >= 1:
        filename = args[0]
    else:
        sys.exit(3)
    if format_to_rst:
        print_rst_file(filename, color_tf, width, to_stdout, bg=dark_light,
                       colors_file=colors_file, style=style_name)
    else:
        syntax_highlight_file(filename, to_stdout, bg=dark_light,
                              colors_file=colors_file, style=style_name)


if __name__ == '__main__':
    main()
