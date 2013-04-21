#!/usr/bin/python
############
# DML Processor
# George Cockshull <george.cockshull@gmail.com>
############

from plyplus import Grammar, STree, SVisitor, STransformer, is_stree
from style import Style
import imp
import types
import argparse
import sys
import re
import platform
from os import path
from pprint import pprint

import cfg


docpreamble = r"""\documentclass[%_document_class_options_%]{%_document_class_%}
\usepackage[%_tikz_package_options_%]{tikz}
\usetikzlibrary{%_tikz_libraries_%}
%_additional_preamble_%
\begin{document}"""

tikzheader = r"""
\begin{tikzpicture}[%_tikzpicture_env_options_%]"""

tikzfooter = r"""
\end{tikzpicture}"""

docpostamble = r"""
\end{document}"""


def _filesearch(fname, ftype='dld'):
    if platform.system() == "Windows":
        dirs = cfg.windows_dirs[ftype]
    else:
        dirs = cfg.fhs_dirs[ftype]
    dirs.insert(0, "")
    if not re.match(".+\.\w+", fname):
        fname += "."+ftype
    for d in dirs:
        try:
            p = path.expandvars(path.expanduser(d+fname)) 
            if cfg.resolver_debug_more:
                print >> sys.stderr, "NOTICE: attempting %s"%p
            f = file(p)
        except IOError:
            f = None
            continue
        break
    if cfg.resolver_debug:
        print >> sys.stderr, "NOTICE: resolving %s -> %s"%(fname, f.name if f is not None else "Not found.")
    if f is None:
        print >> sys.stderr, "PATH ERROR: cannot resolve %s"%fname
    return f


if __name__ == '__main__':

    argparser = argparse.ArgumentParser(description='Diagram Markup Language Processor')
    argparser.add_argument('deffile', metavar='definition file')
    argparser.add_argument('-s', '--src', action='store', dest='sourcefile', type=argparse.FileType('r'))
    argparser.add_argument('-y', '--sty', action='store', dest='stylefile', nargs='*')
    argparser.add_argument('--latex', nargs='?', help='output full latex document with preamble', const='standalone', dest='docclass')
    argparser.add_argument('--ast', help='output AST and render PyDOT AST diagram to ast.png', action='store_true')
    argparser.add_argument('--lex', help='Only lex and output tokens', action='store_true')
    argparser.add_argument('--options', help='additional tikzpicture environment options', action='store', dest='tikzpictureoptions', type=str)
    arg = argparser.parse_args()
    arg.latex = arg.docclass


    #default substitutions
    document_class = arg.latex if arg.latex != None else ''
    document_class_options = ''
    tikz_package_options = ''
    tikzpicture_env_options = '' if not arg.tikzpictureoptions else arg.tikzpictureoptions
    additional_preamble = ''
    tikz_libraries = []
    blind_insert = ''
    
    #initial pre/post function defs
    def preparse(src):
        return src
    def postparse(ast):
        return ast

    #register them
    preparse_funcs = []
    postparse_funcs = []
    preparse_funcs.append(preparse)
    postparse_funcs.append(postparse)

    if(arg.sourcefile==None):
        source = ''
        while 1:
            try: l = raw_input()
            except EOFError: break
            source += l+"\n"
    else:
        source = arg.sourcefile.read()

    #DLD source
    defsrcfile = _filesearch(arg.deffile, 'dld')
    if defsrcfile is None:
        raise IOError("The DLD file you specified was not found")
        exit(1)
    defsrc = defsrcfile.read()

    #include listed styles
    if arg.stylefile is not None:
        #include listed style files
        for f in arg.stylefile:
            defsrc += "\n#style "+f
    else:
        #search for any matching stylesheets and include
        fname = path.basename(arg.deffile).split(".", 1)[0]
        fname += ".dss"
        f = _filesearch(fname, 'dss')
        if f is not None:
            fsrc = f.read()
            if re.match("^#{3,}.*style.*$", fsrc, flags=re.M|re.I):
                defsrc += "\n"+fsrc
            else:
                "\n### style\n"+fsrc
            
    
    #preprocess includes
    def repl(matchobj):
        type, fn, ext = matchobj.groups()
        if ext not in ['dld', 'dss']:
            ext = None

        if type=="include":
            f = _filesearch(fn, 'dld' if ext is None else ext)
        elif type=="style":
            f = _filesearch(fn, 'dss' if ext is None else ext)

        content = f.read() if f is not None else ''

        if type=="include" or re.match("^#{3,}.*style.*$", content, flags=re.M|re.I):
            return content
        else:
            return "### style\n"+content

    include_re = re.compile("^#(include|style)\s+(\S+(\.\w+)?)$", flags = re.M|re.I)
    
    while include_re.search(defsrc):
        defsrc = include_re.sub(repl, defsrc)

    #split file parts
    parts = re.split("^(#{3,}.*)$", defsrc, flags = re.M|re.I)

    grheaders = [i for i,s in enumerate(parts) if re.match("^#{3,}.*grammar.*$", s, flags=re.M|re.I)!=None]
    trheaders = [i for i,s in enumerate(parts) if re.match("^#{3,}.*transform.*$", s, flags=re.M|re.I)!=None]
    pyheaders = [i for i,s in enumerate(parts) if re.match("^#{3,}.*python.*$", s, flags=re.M|re.I)!=None]
    styleheaders = [i for i,s in enumerate(parts) if re.match("^#{3,}.*style.*$", s, flags=re.M|re.I)!=None]

    grsections = [parts[i+1] for i in grheaders if i+1 < len(parts)]
    pysections = [parts[i+1] for i in pyheaders if i+1 < len(parts)]
    stylesections = [parts[i+1] for i in styleheaders if i+1 < len(parts)]

    if len(grheaders) >= 1:
        grammarsrc = '\n'.join(grsections)
    assert grammarsrc

    stylesrc = '\n'.join(stylesections)

    transformer = None
    if len(trheaders) >= 1:
        #construct transformer
        transformer = STransformer()
        for headerindex in trheaders:
            match = re.match("^#{3,}.*transform\s*(\w*).*$" , parts[headerindex], flags=re.M|re.I)
            name = "start" if match==None else match.groups()[0]
            sectindex = headerindex + 1
            assert sectindex < len(parts)
            s = 'def %s(self, tree):\n%s\n_userfunc = %s' % (name, parts[sectindex], name)
            exec s
            setattr(transformer, name, types.MethodType(_userfunc, transformer))

    if len(pyheaders) >= 1:
        for s in pysections:
            exec s
            if preparse != preparse_funcs[-1]:
                preparse_funcs.append(preparse)
            if postparse != postparse_funcs[-1]:
                postparse_funcs.append(postparse)

    #Construct grammar from combined grammar source
    grammar = Grammar(grammarsrc);
    
    #Process styles from combined style source
    styles = Style(stylesrc)
    tikzpicture_env_options = styles.get(elem='tikzpicture', override=tikzpicture_env_options)
    
    #Apply sequence of preparse functions
    for prefunc in preparse_funcs:
        source = prefunc(source)

    #Make substitutions
    docpreamble = docpreamble.replace('%_document_class_%', document_class)
    docpreamble = docpreamble.replace('%_document_class_options_%', document_class_options)
    docpreamble = docpreamble.replace('%_tikz_package_options_%', tikz_package_options)
    docpreamble = docpreamble.replace('%_tikz_libraries_%', ','.join(tikz_libraries))
    docpreamble = docpreamble.replace('%_additional_preamble_%', additional_preamble)
    tikzheader = tikzheader.replace('%_tikzpicture_env_options_%', tikzpicture_env_options)

    if arg.lex:
        for t in grammar.lex(source):
            print "line {0.lineno:<3}col {0.lexpos:<4}{0.type}:\t{0.value}".format(t)
        sys.exit(0)

    #Parse src file according to grammar
    ast = grammar.parse(source)
    ast.calc_parents()
    
    if arg.ast:
        print ast
        import pydot
        ast.to_png_with_pydot("ast.png")
        if transformer:
            ast = transformer.transform(ast)
            print "\npost transform:"
            print ast
            ast.to_png_with_pydot("ast_posttransform.png")
        sys.exit(0)
    
    if arg.latex:
        print docpreamble
    print tikzheader
    styles.push(elem="tikzpicture")
    print blind_insert

    #Apply transformation to AST if one is defined
    if transformer:
        ast = transformer.transform(ast)
        ast.calc_parents()

    #Apply sequence of postparse functions
    for postfunc in postparse_funcs:
        result = postfunc(ast)
        if is_stree(result):
            ast = result
            ast.calc_parents()
            
    styles.pop()
    print tikzfooter
    if arg.latex:
        print docpostamble
        


    
