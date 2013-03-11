

class Graph(object):
    def __init__(self):
        self.nodes = []
        self.edges = []

    def add(self, obj):
        if isinstance(obj, GraphNode):
            self.nodes.append(obj)
            obj.set_num(len(self.nodes)-1)
        elif isinstance(obj, GraphEdge):
            self.edges.append(obj)

    def emit_simple_node_matrix(self, numperrow=1, rowsep='1em', colsep='1em'):
        print r"\matrix[column sep="+colsep+r", row sep="+rowsep+r"] {"
        for num, n in enumerate(self.nodes):
            n.emit()
            if (num+1) % numperrow == 0 or num == len(self.nodes)-1:
                print r"\\"
            else:
                print r"&"
        print r"};"

    def emit_node_matrix(self, rowsep='1em', colsep='1em'):
        self.normalise_node_coords()
        print r"\matrix[column sep="+colsep+r", row sep="+rowsep+r"] {"
        if len(self.nodes) >= 1:
            posdict = {}
            xmax = float('-inf')
            ymax = float('-inf')
            for n in self.nodes:
                posdict[n.pos.__repr__()] = n
                xmax = max(xmax, n.pos[0])
                ymax = max(ymax, n.pos[1])

            for y in range(ymax+1):
                for x in range(xmax+1):
                    poskey = (x,y).__repr__()
                    if poskey in posdict:
                        posdict[poskey].emit()
                    if x<xmax:
                        print " & ",
                print r"\\"
        else:
            print r"  %no nodes"
        print r"};"
    
    def emit_edge_paths(self):
        for e in self.edges:
            src  = self.node_ident(e.src)
            dest = self.node_ident(e.dest)
            if e.label == None:
                print r"\path[%s] (%s) -- (%s);" % (e.cls, src, dest)
            else:
                print r"\path[%s] (%s) -- node{%s} (%s);" % (e.cls, src, e.label, dest)
        

    def normalise_node_coords(self):
        assert len(self.nodes) >= 1
        xmin = ymin = float('inf')
        for n in self.nodes:
            xmin = min(xmin, n.pos[0])
            ymin = min(ymin, n.pos[1])
        for n in self.nodes:
            n.pos = (n.pos[0]-xmin, n.pos[1]-ymin)

    def emit_chain(self):
        print r"{ [start chain] ";
        nprev = None
        for num, n in enumerate(self.nodes):
            fromme = self.edges_from(num)
            tome = self.edges_to(num)
            if not tome:
                print r"\chainin ("+self.node_ident(num)+r");"
            else:
                for s in tome:
                    if s.src == nprev:
                        print r"\chainin ("+self.node_ident(num)+r") [join=by "+s.cls+r"];"

            nprev = num
        print r"};"

    def edges_from(self, nodenum):
        res = []
        for e in self.edges:
            if e.src == nodenum:
                res.append(e)
        return res

    def edges_to(self, nodenum):
        res = []
        for e in self.edges:
            if e.dest == nodenum:
                res.append(e)
        return res

    def node_ident(self, nodenumber):
        return self.nodes[nodenumber].ident
            

class GraphNode():
    def __init__(self, name, cls='draw', ident=None, num=-1, pos=None):
        self.pos = pos
        self.name = name
        self.cls = cls
        self.num = num
        self.ident = "n%s"%num if ident == None else ident

    def emit(self):
        print r"\node["+self.cls+r"] ("+str(self.ident)+r") {"+self.name+r"};",

    def set_num(self, num):
        if self.ident == "n%s"%self.num:
            self.ident = "n%s"%num
        self.num = num
        

class GraphEdge():
    def __init__(self, src, dest, cls='draw', label=None):
        self.src = src
        self.dest = dest
        self.cls = cls
        self.label = label
