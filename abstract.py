

class Graph(object):
    def __init__(self):
        self.nodes = []
        self.edges = []

    def add(self, obj):
        if isinstance(obj, GraphNode):
            self.nodes.append(obj)
        elif isinstance(obj, GraphEdge):
            self.edges.append(obj)

    def emit(self):
        print r"\begin{tikzpicture}"
        print r"\matrix[column sep=0.5cm, row sep=0.5cm] {"
        for n in self.nodes:
            n.emit()
        for e in self.edges:
            e.emit()
        print r"}; \end{tikzpicture}"


class GraphNode():

    def __init__(self, name):
        self.name = name

    def emit(self):
        print r"\node[circle] {"+self.name+r"};"

class GraphEdge():
    
    def __init__(self, name):
        pass
    def emit(self):
        print r"\edge ..."
