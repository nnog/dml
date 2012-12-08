from ply import lex

LEX_TAB_MODULE = "plyplus_grammar_lextab"

tokens = (
        'RULENAME',
        'TOKEN',
        'OPTION',
        'OPER',
        'OR',
        'LPAR',
        'RPAR',
        'COLON',
        'SEMICOLON',
        'REGEXP',
        'SECTION',
        'LCURLY',
        'RCURLY',
#        'COMMENT',
    )

t_RULENAME = '[@#?]?[a-z_][a-z_0-9]*'
t_TOKEN = '[A-Z_][A-Z_0-9]*'
t_OPTION = '%[a-z_]+'

t_OPER = '[?*+]'
t_OR = '\|'
t_LPAR = '\('
t_RPAR = '\)'
t_COLON = ':'
t_SEMICOLON = ';'
t_REGEXP = r"'(.|\n)*?[^\\]'"
t_SECTION = '\#\#\#(.|\\n)*'
t_LCURLY = '{'
t_RCURLY = '}'


def t_COMMENT(t):
    r'//[^\n]*\n|/[*](.|\n)*?[*]/'
    t.lexer.lineno += t.value.count('\n')

def t_NL(t):
    r'\n'
    t.lexer.lineno += 1
    return 0

t_ignore = " \t\r"
def t_error(t):
    raise Exception("Illegal character in grammar: %r in %r" % (t.value[0], t.value[:10] ))

lexer  = lex.lex(lextab=LEX_TAB_MODULE)
