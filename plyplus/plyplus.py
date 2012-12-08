"Author: Erez Shinan, erezshin at gmail.com"

import re, os
import types
import itertools

from ply import lex, yacc

import grammar_parser

from strees import STree, SVisitor, STransformer, is_stree

# -- Must!
#TODO: Support States
#TODO: @ on start symbols should expand them (right now not possible because of technical design issues)
#      alternatively (but not as good?): add option to expand all 'start' symbols

# -- Nice to have
#TODO: Operator precedence
#TODO: find better terms than expand and flatten
#TODO: Exact recovery of input (as text attr)
#      Allow to reconstruct the input with whatever changes were made to the tree
#TODO: Allow 'optimize' mode
#TODO: Rule Self-recursion (an operator? a 'self' keyword?)
#TODO: Add token history on parse error
#TODO: Add rule history on parse error?

# -- Unknown status
#TODO: Allow empty rules
#TODO: Multiply defined tokens (just concatinate with |?)
#TODO: Complete EOF handling in python grammar (postlex)
#TODO: Make filter behaviour consitent for both ()? and ()* / ()+
#TODO: better filters
#TODO: Offer mechanisms to easily avoid ambiguity (expr: expr '\+' expr etc.)
#TODO: Use PLY's ignore mechanism (=tokens return None) instead of post-filtering it myself?
#TODO: Support Compiling grammars into a single parser python file
#TODO: Support running multi-threaded
#TODO: Better debug mode (set debug level, choose between prints and interactive debugging?)

# -- Continual Tasks
#TODO: Optimize for space
#TODO: Optimize for speed
#TODO: require less knowledge of ply
#TODO: meaningful names to anonymous tokens

# -- Done
#DONE: anonymous tokens
#DONE: Resolve errors caused by dups of tokens
#DONE: Allow comments in grammar
#DONE: (a+)? is different from a*
#       print_stmt : PRINT (RIGHTSHIFT? test (COMMA test)* COMMA?)?  ;
#           --> only works as -->
#       print_stmt : PRINT (RIGHTSHIFT? test ((COMMA test)+)? COMMA?)?  ;
#
#      Similarly:
#      dictmaker : test COLON test (COMMA test COLON test)* COMMA? ;
#           --> only works as -->
#      dictmaker : test COLON test (COMMA test COLON test)+? COMMA? ;
#DONE: rename simps
#DONE: Recursive parsing
#DONE: Change rule+ into "rule simp*" instead of "simp+"
#DONE: Multi-line comments
#DONE: Better error handling (choose between prints and raising exception, setting threshold, etc.)
#


def get_token_name(token, default):
    return {
        ':' : 'COLON',
        ',' : 'COMMA',
        ';' : 'SEMICOLON',
        '+' : 'PLUS',
        '-' : 'MINUS',
        '*' : 'STAR',
        '/' : 'SLASH',
        '|' : 'VBAR',
        '!' : 'BANG',
        '?' : 'QMARK',
        '#' : 'HASH',
        '$' : 'DOLLAR',
        '&' : 'AMPERSAND',
        '<' : 'LESSTHAN',
        '>' : 'MORETHAN',
        '=' : 'EQUAL',
        '.' : 'DOT',
        '%' : 'PERCENT',
        '`' : 'BACKQUOTE',
        '^' : 'CIRCUMFLEX',
        '"' : 'DBLQUOTE',
        '\'' : 'QUOTE',
        '~' : 'TILDE',
        '@' : 'AT',
        '(' : 'LPAR',
        ')' : 'RPAR',
        '{' : 'LBRACE',
        '}' : 'RBRACE',
        '[' : 'LSQB',
        ']' : 'RSQB',
    }.get( token, default)

class PlyplusException(Exception): pass

class GrammarException(PlyplusException): pass

class TokenizeError(PlyplusException): pass

class ParseError(PlyplusException): pass

class RuleMods(object):
    EXPAND = '@'    # Expand all instances of rule
    FLATTEN = '#'   # Expand all nested instances of rule
    EXPAND1 = '?'   # Expand all instances of rule with only one child


class ExtractSubgrammars_Visitor(SVisitor):
    def __init__(self, parent_source_name, parent_tab_filename, parent_options):
        self.parent_source_name = parent_source_name
        self.parent_tab_filename = parent_tab_filename
        self.parent_options = parent_options

        self.last_tok = None

    def pre_tokendef(self, tok):
        self.last_tok = tok.tail[0]
    def subgrammar(self, tree):
        assert self.last_tok
        assert len(tree.tail) == 1
        source_name = '%s:%s'%(self.parent_source_name, self.last_tok.lower())
        tab_filename = '%s_%s'%(self.parent_tab_filename, self.last_tok.lower())
        subgrammar = _Grammar(tree.tail[0], source_name, tab_filename, **self.parent_options)
        tree.head, tree.tail = 'subgrammarobj', [subgrammar]

class ApplySubgrammars_Visitor(SVisitor):
    def __init__(self, subgrammars):
        self.subgrammars = subgrammars
    def __default__(self, tree):
        for i,tok in enumerate(tree.tail):
            if type(tok) == TokValue and tok.type in self.subgrammars:
                parsed_tok = self.subgrammars[tok.type].parse(tok)
                assert parsed_tok.head == 'start'
                tree.tail[i] = parsed_tok


class CollectTokenDefs_Visitor(SVisitor):
    def __init__(self, dict_to_populate):
        self.tokendefs = dict_to_populate

    def tokendef(self, tree):
        self.tokendefs[ tree.tail[0] ] = tree

    def fragmentdef(self, tree):
        self.tokendefs[ tree.tail[0] ] = tree

def _unescape_token_def(token_def):
    assert token_def[0] == "'" == token_def[-1]
    return token_def[1:-1].replace(r"\'", "'")

class SimplifyTokenDefs_Visitor(SVisitor):

    def __init__(self):
        self.tokendefs = {}

    def visit(self, tree):
        CollectTokenDefs_Visitor(self.tokendefs).visit(tree)
        SVisitor.visit(self, tree)

        for tokendef in self.tokendefs.itervalues():
            self._simplify_token(tokendef)

        return self.tokendefs

    def _simplify_token(self, tokendef):
        token_value = tokendef.tail[1]
        if is_stree(token_value):
            assert token_value.head == 'tokenvalue'

            regexp = ''.join( _unescape_token_def(d) if d.startswith("'") else self._simplify_token(self.tokendefs[d])
                                for d in token_value.tail )
            tokendef.tail = list(tokendef.tail) # can't assign to a tuple
            tokendef.tail[1] = regexp

        return tokendef.tail[1]

class NameAnonymousTokens_Visitor(SVisitor):
    ANON_TOKEN_ID = 'ANON'

    def __init__(self, tokendefs):
        self._count = itertools.count()
        self._rules_to_add = []

        self.token_name_from_value = {}
        for name, tokendef in tokendefs.iteritems():
            self.token_name_from_value[tokendef.tail[1]] = name

    def _get_new_tok_name(self, tok):
        return '_%s_%d' % (get_token_name(tok[1:-1], self.ANON_TOKEN_ID), self._count.next())

    def rule(self, tree):
        for i, child in enumerate(tree.tail):
            if isinstance(child, str) and child.startswith("'"):
                child = _unescape_token_def(child)
                try:
                    tok_name = self.token_name_from_value[child]
                except KeyError:
                    tok_name = self._get_new_tok_name(child) # Add anonymous token
                    self.token_name_from_value[child] = tok_name    # for future anonymous occurences
                    self._rules_to_add.append(STree('tokendef', [tok_name, child]))
                tree.tail[i] = tok_name

    def grammar(self, tree):
        if self._rules_to_add:
            tree.tail += self._rules_to_add


class SimplifyGrammar_Visitor(SVisitor):
    ANON_RULE_ID = 'anon'

    def __init__(self):
        self._count = itertools.count()
        self._rules_to_add = []

    def _get_new_rule_name(self):
        return '_%s_%d' % (self.ANON_RULE_ID, self._count.next())

    def _flatten(self, tree):
        to_expand = [i for i, subtree in enumerate(tree.tail) if is_stree(subtree) and subtree.head == tree.head]
        if to_expand:
            tree.expand_kids(*to_expand)
        return bool(to_expand)

    def _visit(self, tree):
        "_visit simplifies the tree as much as possible"
        # visit until nothing left to change (not the most efficient, but good enough since it's only the grammar)
        while SVisitor._visit(self, tree):
            pass

    def grammar(self, tree):
        changed = self._flatten(tree)

        if self._rules_to_add:
            changed = True
            tree.tail += self._rules_to_add
            self._rules_to_add = []
        return changed

    def _add_recurse_rule(self, mod, name, repeated_expr):
        new_rule = STree('ruledef', [mod+name, STree('rules_list', [STree('rule', [repeated_expr]), STree('rule', [name, repeated_expr])]) ])
        self._rules_to_add.append(new_rule)
        return new_rule

    def oper(self, tree):
        rule_operand, operator = tree.tail

        if operator == '*':
            # a : b c* d;
            #  --> in theory
            # a : b _c d;
            # _c : c _c |;
            #  --> in practice (much faster with PLY, approx x2)
            # a : b _c d | b d;
            # _c : _c c | c;
            new_name = self._get_new_rule_name() + '_star'
            self._add_recurse_rule(RuleMods.EXPAND, new_name, rule_operand)
            tree.head, tree.tail = 'rules_list', [STree('rule', [new_name]), STree('rule', [])]
        elif operator == '+':
            # a : b c+ d;
            #  -->
            # a : b _c d;
            # _c : _c c | c;
            new_name = self._get_new_rule_name() + '_plus'
            self._add_recurse_rule(RuleMods.EXPAND, new_name, rule_operand)
            tree.head, tree.tail = 'rule', [new_name]
        elif operator == '?':
            tree.head, tree.tail = 'rules_list', [rule_operand, STree('rule', [])]
        else:
            assert False, rule_operand

        return True # changed

    def rule(self, tree):
        # rules_list unpacking
        # a : b (c|d) e
        #  -->
        # a : b c e | b d e
        #
        # In actual terms:
        #
        # [rule [b] [rules_list [c] [d]] [e]]
        #   -->
        # [rules_list [rule [b] [c] [e]] [rule [b] [d] [e]] ]
        #
        changed = False

        if self._flatten(tree):
            changed = True

        for i,child in enumerate(tree.tail):
            if is_stree(child) and child.head == 'rules_list':
                # found. now flatten
                new_rules_list = []
                for option in child.tail:
                    new_rules_list.append(STree('rule', []))
                    # for each rule in rules_list
                    for j,child2 in enumerate(tree.tail):
                        if j == i:
                            new_rules_list[-1].tail.append(option)
                        else:
                            new_rules_list[-1].tail.append(child2)
                tree.head, tree.tail = 'rules_list', new_rules_list
                return True # changed

        return changed # Not changed

    modtokenlist = _flatten
    tokenmods = _flatten
    tokenvalue = _flatten
    number_list = _flatten
    rules_list = _flatten



class ToPlyGrammar_Tranformer(STransformer):
    """Transforms grammar into ply-compliant grammar
    This is only a partial transformation that should be post-processd in order to apply
    XXX Probably a bad class name
    """
    def rules_list(self, tree):
        return '\n\t| '.join(tree.tail)

    def rule(self, tree):
        return ' '.join(tree.tail)

    def extrule(self, tree):
        return ' '.join(tree.tail)

    def oper(self, tree):
        return '(%s)%s'%(' '.join(tree.tail[:-1]), tree.tail[-1])

    def ruledef(self, tree):
        return STree('rule', (tree.tail[0], '%s\t: %s'%(tree.tail[0], tree.tail[1])))

    def optiondef(self, tree):
        return STree('option', tree.tail)

    def fragmentdef(self, tree):
        return STree('fragment', [None, None])

    def tokendef(self, tree):
        if len(tree.tail) > 2:
            return STree('token_with_mods', [tree.tail[0], tree.tail[1:]])
        else:
            return STree('token', tree.tail)

    def grammar(self, tree):
        return tree.tail

    def extgrammar(self, tree):
        return tree.tail


class SimplifySyntaxTree_Visitor(SVisitor):
    def __init__(self, rules_to_flatten, rules_to_expand):
        self.rules_to_flatten = frozenset(rules_to_flatten)
        self.rules_to_expand = frozenset(rules_to_expand)

    def __default__(self, tree):
        # Expand/Flatten rules if requested in grammar
        to_expand = [i for i, subtree in enumerate(tree.tail) if is_stree(subtree) and (
                        (subtree.head == tree.head and subtree.head in self.rules_to_flatten)
                        or (subtree.head in self.rules_to_expand)
                    ) ]
        if to_expand:
            tree.expand_kids(*to_expand)

        # Remove empty trees ( XXX not strictly necessary, just cleaner... should I keep them?)
        to_remove = [i for i, subtree in enumerate(tree.tail) if is_stree(subtree) and not subtree.tail]
        if to_remove:
            tree.remove_kids(*to_remove)

class FilterTokens_Tranformer(STransformer):
    def __default__(self, tree):
        if len(tree.tail) <= 1:
            return tree
        return tree.__class__(tree.head, [x for x in tree.tail if is_stree(x)])

class TokValue(str):
    def __new__(cls, s, type=None, line=None, column=None, pos_in_stream=None, index=None):
        inst = str.__new__(cls,s)
        inst.type = type
        inst.line = line
        inst.column = column
        inst.pos_in_stream = pos_in_stream
        inst.index = index
        return inst

    def __repr__(self):
        if self.line and self.column:
            return repr("%s:%s|%s"%(self.line, self.column, self))
        return str.__repr__(self)

class LexerWrapper(object):
    def __init__(self, lexer, newline_tokens_names, newline_char='\n', ignore_token_names=()):
        self.lexer = lexer
        self.newline_tokens_names = set(newline_tokens_names)
        self.ignore_token_names = ignore_token_names
        self.newline_char = newline_char

        self.current_state = lexer.current_state
        self.begin = lexer.begin

    def input(self, s):
        self.lineno = 1
        self._lexer_pos_of_start_column = -1
        self._tok_count = 0
        return self.lexer.input(s)

    def token(self):
        # get a new token that shouldn't be %ignored
        while True:
            self._tok_count += 1

            t = self.lexer.token()
            if not t:
                return t    # End of stream

            try:
                if t.type not in self.ignore_token_names:
                    self._wrap_token(t)
                    return t
            finally:
                # handle line and column
                # must happen after assigning, because we change _lexer_pos_of_start_column
                # in other words, we want to apply the token's effect to the lexer, not to itself
                if t.type in self.newline_tokens_names:
                    self._handle_newlines(t)


    def _wrap_token(self, t):
        tok_value = TokValue(t.value,
                        line = self.lineno,
                        column = t.lexpos-self._lexer_pos_of_start_column,
                        pos_in_stream = t.lexpos,
                        type = t.type,
                        index = self._tok_count,
                    )

        if hasattr(t, 'lexer'):
            t.lexer.lineno = self.lineno    # not self.lexer, because it may be another wrapper

        t.lineno = self.lineno
        t.value = tok_value

    def _handle_newlines(self, t):
        newlines = t.value.count(self.newline_char)
        self.lineno += newlines

        if newlines:
            self._lexer_pos_of_start_column = t.lexpos + t.value.rindex(self.newline_char)


class Grammar(object):
    def __init__(self, grammar, **options):
        if isinstance(grammar, file):
            # PLY turns "a.b" into "b", so gotta get rid of the dot.
            tab_filename = "parsetab_%s" % os.path.split(grammar.name)[1].replace('.', '_')
            source = grammar.name
            grammar = grammar.read()
        else:
            assert isinstance(grammar, str)
            tab_filename = "parsetab_%s" % str(hash(grammar)%(2L**32))
            source = '<string>'

        grammar_tree = grammar_parser.parse(grammar)
        if not grammar_tree:
            raise GrammarException("Parse Error: Could not create grammar")

        self._grammar = _Grammar(grammar_tree, source, tab_filename, **options)

    def lex(self, text):
        return self._grammar.lex(text)

    def parse(self, text):
        return self._grammar.parse(text)

class _Grammar(object):
    def __init__(self, grammar_tree, source_name, tab_filename, **options):
        self.options = dict(options)
        self.debug=bool(options.pop('debug', False))
        self.just_lex=bool(options.pop('just_lex', False))
        self.ignore_postproc=bool(options.pop('ignore_postproc', False))
        self.auto_filter_tokens=bool(options.pop('auto_filter_tokens', True))
        if options:
            raise TypeError("Unknown options: %s"%options.keys())

        self.tab_filename = tab_filename
        self.source_name = source_name
        self.tokens = []    # for lex module
        self.rules_to_flatten = []
        self.rules_to_expand = []
        self._newline_tokens = set()
        self._ignore_tokens = set()
        self.lexer_postproc = None
        self._newline_value = '\n'

        # -- Build Grammar --
        self.subgrammars = {}
        ExtractSubgrammars_Visitor(source_name, tab_filename, self.options).visit(grammar_tree)
        SimplifyGrammar_Visitor().visit(grammar_tree)
        tokendefs = SimplifyTokenDefs_Visitor().visit(grammar_tree)
        NameAnonymousTokens_Visitor(tokendefs).visit(grammar_tree)
        ply_grammar_and_code = ToPlyGrammar_Tranformer().transform(grammar_tree)

        self.STree = STree

        # code may be omitted
        if len(ply_grammar_and_code) == 1:
            ply_grammar, = ply_grammar_and_code
        else:
            ply_grammar, code = ply_grammar_and_code
            exec(code)

        for x in ply_grammar:
            type, (name, defin) = x.head, x.tail
            assert type in ('token', 'token_with_mods', 'rule', 'option', 'fragment'), "Can't handle type %s"%type
            handler = getattr(self, '_add_%s' % type)
            handler(name, defin)

        # -- Build lexer --
        lexer = lex.lex(module=self)
        lexer = LexerWrapper(lexer, newline_tokens_names=self._newline_tokens, newline_char=self._newline_value, ignore_token_names=self._ignore_tokens)
        if self.lexer_postproc and not self.ignore_postproc:
            lexer = self.lexer_postproc(lexer)  # apply wrapper
        self.lexer = lexer

        # -- Build Parser --
        if not self.just_lex:
            self.parser = yacc.yacc(module=self, debug=self.debug, tabmodule=tab_filename)

    def __repr__(self):
        return '<Grammar from %s, tab at %s>' % (self.source_name, self.tab_filename)

    def lex(self, text):
        "Performs tokenizing as a generator"
        self.lexer.input(text)
        while True:
            tok = self.lexer.token()
            if not tok:
                break
            yield tok

    def parse(self, text):
        "Parse the text into an AST"
        assert not self.just_lex

        self.errors = []
        tree = self.parser.parse(text, lexer=self.lexer, debug=self.debug)
        if not tree:
            self.errors.append("Could not create parse tree!")
        if self.errors:
            raise ParseError('\n'.join(self.errors))

        # Apply subgrammars
        if self.subgrammars:
            ApplySubgrammars_Visitor(self.subgrammars).visit(tree)

        # Apply auto-filtering (remove 'punctuation' tokens)
        if self.auto_filter_tokens:
            tree = FilterTokens_Tranformer().transform(tree)

        SimplifySyntaxTree_Visitor(self.rules_to_flatten, self.rules_to_expand).visit(tree)

        return tree

    def _add_fragment(self, _1, _2):
        pass

    def _add_option(self, name, defin):
        "Set an option"
        if name == '%newline_char':
            self._newline_value = eval(defin)   # XXX BAD BAD! I have TODO it differently
        else:
            raise GrammarException( "Unknown option: %s " % name )

    def _add_token_with_mods(self, name, defin):
        token_value, token_features = defin

        token_added = False
        if token_features.head == 'subgrammarobj':
            assert len(token_features.tail) == 1
            self.subgrammars[name] = token_features.tail[0]
        elif token_features.head == 'tokenmods':
            for token_mod in token_features.tail:
                mod, modtokenlist = token_mod.tail

                if mod == '%unless':
                    assert not token_added, "token already added, can't issue %unless"
                    unless_toks_dict = {}
                    unless_toks_regexps = []
                    for modtoken in modtokenlist.tail:
                        assert modtoken.head == 'token'
                        modtok_name, modtok_value = modtoken.tail


                        self._add_token(modtok_name, modtok_value)

                        if not re.search('[^\w/-]', modtok_value):   # definitely not a regexp, let's optimize it
                            unless_toks_dict[modtok_value] = modtok_name
                        else:
                            if not modtok_value.startswith('^'):
                                modtok_value = '^' + modtok_value
                            if not modtok_value.endswith('$'):
                                modtok_value = modtok_value + '$'
                            unless_toks_regexps += [(modtok_value, modtok_name)]

                    unless_toks_regexps.sort(key=lambda x:x[0].__len__(), reverse=True)

                    self.tokens.append(name)

                    code = ('\tt.type = self._%s_unless_toks_dict.get(t.value, %r)\n' % (name, name)
                           +'\tfor regexp, tokname in self._%s_unless_toks_regexps:\n' % (name,)
                           +'\t\tif re.match(regexp, t.value):\n'
                           +'\t\t\tt.type = tokname\n'
                           +'\t\t\tbreak\n'
                           +'\treturn t')
                    s = ('def t_%s(self, t):\n\t%s\n%s\nx = t_%s\n'
                        %(name, repr(token_value), code, name))
                    exec(s)

                    setattr(self, 't_%s'%name, x.__get__(self))
                    setattr(self, '_%s_unless_toks_dict'%name, unless_toks_dict)
                    setattr(self, '_%s_unless_toks_regexps'%name, unless_toks_regexps)

                    token_added = True

                elif mod == '%newline':
                    assert len(modtokenlist.tail) == 0
                    self._newline_tokens.add(name)

                elif mod == '%ignore':
                    assert len(modtokenlist.tail) == 0
                    self._ignore_tokens.add(name)
                else:
                    raise GrammarException("Unknown token modifier: %s" % mod)
        else:
            raise GrammarException("Unknown token feature: %s" % token_features.head)

        if not token_added:
            self._add_token(name, token_value)

    def _add_token(self, name, token_value):
        assert isinstance(token_value, str)
        self.tokens.append(name)
        setattr(self, 't_%s'%name, token_value)

    def _add_rule(self, rule_name, rule_def):
        mods, name = re.match('([@#?]*)(.*)', rule_name).groups()
        if mods:
            assert rule_def[:len(mods)] == mods
            rule_def = rule_def[len(mods):]
            rule_name = rule_name[len(mods):]

        if RuleMods.EXPAND in mods:
            self.rules_to_expand.append( rule_name )
        elif RuleMods.FLATTEN in mods:
            self.rules_to_flatten.append( rule_name )

        if RuleMods.EXPAND1 in mods or RuleMods.EXPAND in mods:  # EXPAND is here just for the speed-up
            code = '\tp[0] = self.STree(%r, p[1:]) if len(p)>2 else p[1]' % (rule_name,)
        else:
            code = '\tp[0] = self.STree(%r, p[1:])' % (rule_name,)
        s = ('def p_%s(self, p):\n\t%r\n%s\nx = p_%s\n'
            %(rule_name, rule_def, code, rule_name))
        exec(s)

        setattr(self, 'p_%s'%rule_name, types.MethodType(x, self))


    @staticmethod
    def t_error(t):
        raise TokenizeError("Illegal character in input: '%s', line: %s, %s" % (t.value[:32], t.lineno, t.type))

    def p_error(self, p):
        if p:
            if isinstance(p.value, TokValue):
                msg = "Syntax error in input at '%s' (type %s) line %s col %s" % (p.value, p.type, p.value.line, p.value.column)
            else:
                msg = "Syntax error in input at '%s' (type %s) line %s" % (p.value, p.type, p.lineno)
        else:
            msg = "Syntax error in input (details unknown): %s" % p

        if self.debug:
            print msg

        self.errors.append(msg)

    start = "start"


