from plyplus import Grammar
import imp
import argparse

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

if __name__ == '__main__':

    argparser = argparse.ArgumentParser(description='Diagram Markup Language Processor')
    argparser.add_argument('deffile', metavar='definition file', action='store', type=argparse.FileType('r'))
    argparser.add_argument('-s', '--src', action='store', dest='sourcefile', type=argparse.FileType('r'))
    argparser.add_argument('--latex', help='output full latex document with preamble', action='store_true')
    argparser.add_argument('--renderast', help='also render AST to ast.png', action='store_true')
    argparser.add_argument('--options', help='additional tikzpicture environment options', action='store', dest='tikzpictureoptions', type=str)
    arg = argparser.parse_args()


    if(arg.sourcefile==None):
        s = ''
        while 1:
            try: l = raw_input()
            except EOFError: break
            s += l
    else:
        s = arg.sourcefile.read()
        
    (grammar, py) = arg.deffile.read().split("###")
    g = Grammar(grammar);

    #load python code into its own module
    m = imp.new_module("tempdmlmodule")
    exec py in m.__dict__

    #default substitutions
    document_class = 'minimal'
    document_class_options = ''
    tikz_package_options = ''
    tikzpicture_env_options = '' if not arg.tikzpictureoptions else arg.tikzpictureoptions
    additional_preamble = ''
    tikz_libraries = []

    s = m.preparse(s)

    #make substitutions
    docpreamble = docpreamble.replace('%_document_class_%', document_class)
    docpreamble = docpreamble.replace('%_document_class_options_%', document_class_options)
    docpreamble = docpreamble.replace('%_tikz_package_options_%', tikz_package_options)
    docpreamble = docpreamble.replace('%_tikz_libraries_%', ','.join(tikz_libraries))
    docpreamble = docpreamble.replace('%_additional_preamble_%', additional_preamble)
    tikzheader = tikzheader.replace('%_tikzpicture_env_options_%', tikzpicture_env_options)
    
    
    if arg.latex:
        print docpreamble
    print tikzheader

    ast = g.parse(s)
    m.postparse(ast)

    print tikzfooter
    if arg.latex:
        print docpostamble
        

    if arg.renderast:
        import pydot
        ast.to_png_with_pydot("ast.png");



    
