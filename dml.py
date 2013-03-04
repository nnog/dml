from plyplus import Grammar, STree, SVisitor, STransformer, is_stree
import imp
import types
import argparse
import sys
import re
from pprint import pprint

docpreamble = r"""
\documentclass[%_document_class_options_%]{%_document_class_%}
\usepackage[%_tikz_package_options_%]{tikz}
\usetikzlibrary{%_tikz_libraries_%}
%_additional_preamble_%
\begin{document}
"""

tikzheader = r"""
\begin{tikzpicture}[%_tikzpicture_env_options_%]
"""

tikzfooter = r"""
\end{tikzpicture}
"""

docpostamble = r"""
\end{document}
"""

#debug
def pretty(lis):
    print "\n==================next\n".join(lis)


if __name__ == '__main__':

    argparser = argparse.ArgumentParser(description='Diagram Markup Language Processor')
    argparser.add_argument('deffile', metavar='definition file', action='store', type=argparse.FileType('r'))
    argparser.add_argument('-s', '--src', action='store', dest='sourcefile', type=argparse.FileType('r'))
    argparser.add_argument('--latex', help='output full latex document with preamble', action='store_true')
    argparser.add_argument('--ast', help='output AST and render PyDOT AST diagram to ast.png', action='store_true')
    argparser.add_argument('--options', help='additional tikzpicture environment options', action='store', dest='tikzpictureoptions', type=str)
    arg = argparser.parse_args()


    if(arg.sourcefile==None):
        source = ''
        while 1:
            try: l = raw_input()
            except EOFError: break
            source += l
    else:
        source = arg.sourcefile.read()

    defsrc = arg.deffile.read()
    
    #preprocess includes
    def repl(matchobj):
        fn, ext = matchobj.groups()
        filename = fn+".dld" if ext==None else fn+ext
        return file(filename).read()

    include_re = re.compile("^#+include\s+(\w+)(\.\w+)?$", flags = re.M|re.I)
    
    while include_re.match(defsrc):
        defsrc = include_re.sub(repl, defsrc)

    #split file parts
    parts = re.split("^(#{3,}.*)$", defsrc, flags = re.M|re.I)

    grheaders = [i for i,s in enumerate(parts) if re.match("^#{3,}.*grammar.*$", s, flags=re.M|re.I)!=None]
    trheaders = [i for i,s in enumerate(parts) if re.match("^#{3,}.*transform.*$", s, flags=re.M|re.I)!=None]
    pyheaders = [i for i,s in enumerate(parts) if re.match("^#{3,}.*python.*$", s, flags=re.M|re.I)!=None]

    grsections = [parts[i+1] for i in grheaders if i+1 < len(parts)]
    pysections = [parts[i+1] for i in pyheaders if i+1 < len(parts)]

    if len(grheaders) >= 1:
        grammarsrc = '\n'.join(grsections)
    assert grammarsrc
        
    transformer = None
    if len(trheaders) >= 1:
        transformer = STransformer()
        for headerindex in trheaders:
            match = re.match("^#{3,}.*transform\s*(\w*).*$" , parts[headerindex], flags=re.M|re.I)
            name = "start" if match==None else match.groups()[0]
            sectindex = headerindex + 1
            assert sectindex < len(parts)
            s = 'def %s(self, tree):\n%s\n_userfunc = %s' % (name, parts[sectindex], name)
            exec s
            setattr(transformer, name, types.MethodType(_userfunc, transformer))


    #default pre/post function defs
    def preparse(src):
        return src
    def postparse(ast):
        return ast


    #default substitutions
    document_class = 'minimal'
    document_class_options = ''
    tikz_package_options = ''
    tikzpicture_env_options = '' if not arg.tikzpictureoptions else arg.tikzpictureoptions
    additional_preamble = ''
    tikz_libraries = []
    
    py = None
    postparse_funcs = []
    if len(pyheaders) >= 1:
        for s in pysections:
            exec s
            postparse_funcs.append(postparse)

    grammar = Grammar(grammarsrc);
    
    source = preparse(source)

    #make substitutions
    docpreamble = docpreamble.replace('%_document_class_%', document_class)
    docpreamble = docpreamble.replace('%_document_class_options_%', document_class_options)
    docpreamble = docpreamble.replace('%_tikz_package_options_%', tikz_package_options)
    docpreamble = docpreamble.replace('%_tikz_libraries_%', ','.join(tikz_libraries))
    docpreamble = docpreamble.replace('%_additional_preamble_%', additional_preamble)
    tikzheader = tikzheader.replace('%_tikzpicture_env_options_%', tikzpicture_env_options)

    #parse src file according to grammar
    ast = grammar.parse(source)
    
    if arg.ast:
        print ast
        import pydot
        ast.to_png_with_pydot("ast.png")
        if transformer:
            ast = transformer.transform(ast)
            print "\npost transform:\n"
            print ast
            ast.to_png_with_pydot("ast_posttransform.png")
        sys.exit(0)
    
    if arg.latex:
        print docpreamble
    print tikzheader

    #apply transformation to AST if one is defined
    if transformer:
        ast = transformer.transform(ast)

    #apply sequence of postparse functions
    if postparse_funcs:
        for postfunc in postparse_funcs:
            res = postfunc(ast)
            if is_stree(res):
                ast = res

    print tikzfooter
    if arg.latex:
        print docpostamble
        


    
