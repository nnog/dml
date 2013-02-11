

class Graph(object):
    def __init__(self):
        self.nodes = []
        self.edges = []

    def add(self, obj):
        if isinstance(obj, GraphNode):
            self.nodes.append(obj)
            obj.num = len(self.nodes)-1
        elif isinstance(obj, GraphEdge):
            self.edges.append(obj)

    def emit_node_matrix(self, numperrow=1, sep='5mm'):
        print r"\matrix[column sep="+sep+r", row sep="+sep+r"] {"
        for num, n in enumerate(self.nodes):
            n.emit()
            if (num+1) % numperrow == 0 or num == len(self.nodes)-1:
                print r"\\"
            else:
                print r"&"
        print r"};"

    def emit_chain(self):
        print r"{ [start chain] ";
        nprev = None
        for num, n in enumerate(self.nodes):
            fromme = self.edges_from(num)
            tome = self.edges_to(num)
            if not tome:
                print r"\chainin (n"+str(num)+r");"
            else:
                for s in tome:
                    if s.src == nprev:
                        print r"\chainin (n"+str(num)+r") [join=by "+s.cls+r"];"

            #TODO: branching based on edges from this one (that arent the next)

            nprev = num
        print r"};"

    def edges_from(self, node):
        res = []
        for e in self.edges:
            if e.src == node:
                res.append(e)
        return res

    def edges_to(self, node):
        res = []
        for e in self.edges:
            if e.dest == node:
                res.append(e)
        return res

    def node_search(self):
        return len(self.nodes)-1


class GraphNode():

    def __init__(self, name, cls='draw', num=-1):
        self.name = name
        self.cls = cls
        self.num = num

    def emit(self):
        print r"\node["+self.cls+r"] (n"+str(self.num)+r") {"+self.name+r"};",

class GraphEdge():
    def __init__(self, src, dest, cls='->,>=latex'):
        self.src = src
        self.dest = dest
        self.cls = cls
