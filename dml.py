from plyplus import Grammar
import pydot

if __name__ == '__main__':
    fname = "test.dld"
    s = raw_input("> ")
    (grammar, py) = file(fname).read().split("###")
    g = Grammar(grammar);
    ast = g.parse(s)
    ast.to_png_with_pydot("ast.png");
    exec py
