from plyplus import Grammar
import imp
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
    parts = re.split("^(#{3,}.*)$", defsrc, flags = re.M|re.I)

    grheaders = [i for i,s in enumerate(parts) if re.match("^#{3,}.*grammar.*$", s, flags=re.M|re.I)!=None]
    trheaders = [i for i,s in enumerate(parts) if re.match("^#{3,}.*transformer.*$", s, flags=re.M|re.I)!=None]
    pyheaders = [i for i,s in enumerate(parts) if re.match("^#{3,}.*python.*$", s, flags=re.M|re.I)!=None]

    grsections = [parts[i+1] for i in grheaders if i+1 < len(parts)]
    trsections = [parts[i+1] for i in trheaders if i+1 < len(parts)]
    pysections = [parts[i+1] for i in pyheaders if i+1 < len(parts)]

    if len(grheaders) == 0:
        grammar = parts[0]
    else:
        grammar = '\n'.join(grsections)
        
    using_transformer = False
    if len(trheaders) >= 1:
        using_transformer = True
        transformer = '\n'.join(trsections)

    if len(pyheaders) == 0:
        py = parts[-1]
    else:
        py = '\n'.join(pysections)

    
    g = Grammar(grammar);


    #default substitutions
    document_class = 'minimal'
    document_class_options = ''
    tikz_package_options = ''
    tikzpicture_env_options = '' if not arg.tikzpictureoptions else arg.tikzpictureoptions
    additional_preamble = ''
    tikz_libraries = []

    exec py

    source = preparse(source)

    #make substitutions
    docpreamble = docpreamble.replace('%_document_class_%', document_class)
    docpreamble = docpreamble.replace('%_document_class_options_%', document_class_options)
    docpreamble = docpreamble.replace('%_tikz_package_options_%', tikz_package_options)
    docpreamble = docpreamble.replace('%_tikz_libraries_%', ','.join(tikz_libraries))
    docpreamble = docpreamble.replace('%_additional_preamble_%', additional_preamble)
    tikzheader = tikzheader.replace('%_tikzpicture_env_options_%', tikzpicture_env_options)

    if arg.ast:
        ast = g.parse(s)
        print ast
        import pydot
        ast.to_png_with_pydot("ast.png");
        sys.exit(0)
    
    if arg.latex:
        print docpreamble
    print tikzheader

    ast = g.parse(source)

    print 
    postparse(ast)

    print tikzfooter
    if arg.latex:
        print docpostamble
        


    
