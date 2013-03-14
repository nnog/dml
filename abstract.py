

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
            posstr = '[%s]'%e.labelpos if e.labelpos!=None else ''
            labelstr = 'node%s{%s}'%(posstr, e.label) if e.label else ''
            startface = '.%s'%e.startface if e.startface!=None else ''
            print r"\path[%s] (%s%s) %s %s %s (%s);" % (e.cls, e.src, startface, e.leg, labelstr, e.route, e.dest)
        
    def route_edges(self):
        for e in self.edges:
            src = self.node_search(e.src)
            dest = self.node_search(e.dest)
            diffx = dest.pos[0] - src.pos[0]
            diffy = dest.pos[1] - src.pos[1]
            if (diffx == 0 and diffy == 1) or (abs(diffx) == 1 and diffy == 0):
                continue #trivial
            elif diffx == 0 and (abs(diffy) >= 2 or diffy < 0):
                lwidth = "%sem"%len(e.label) if e.label != None and len(e.label)>1 else "1.0"
                if e.startface == 'east':
                    e.route = '++(%s,0) |-'%lwidth
                elif e.startface == 'west':
                    e.route = '++(-%s,0) |-'%lwidth
                else:
                    e.startface = e.endface = 'east'
                    e.route = '++(1em,0) |-'
            elif abs(diffx) >= 1 and abs(diffy) >= 1:
                ####TODO: this is a naive check - only correct for abs(diffs) = 1
                #could go full out path finding maybe? or just something in between
                xy_clear = self.pos_get((src.pos[0]+diffx, src.pos[1])) == None
                yx_clear = self.pos_get((src.pos[0], src.pos[1]+diffy)) == None
                if xy_clear:
                    e.leg = '-|'
                elif yx_clear:
                    e.leg = '|-'
                    
                    
   
    def normalise_node_coords(self):
        if len(self.nodes) == 0: return
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

    def edges_from(self, nodeident):
        return [e for e in self.edges if e.src==nodeident]

    def edges_to(self, nodeident):
        return [e for e in self.edges if e.dest==nodeident]

    def terminal_nodes(self):
        return [n for n in self.nodes if len(self.edges_from(n.ident))==0 or len(self.edges_to(n.ident))==0]

    def forking_nodes(self):
        return [n for n in self.nodes if len(self.edges_from(n.ident))>1 and len(self.edges_to(n.ident))>=1]

    def node_ident(self, nodenumber):
        return self.nodes[nodenumber].ident

    def node_search(self, ident):
        for n in self.nodes:
            if n.ident == ident:
                return n
        raise NameError("Node identifier '%s' cannot be resolved."%ident)

    def pos_get(self, pos):
        for n in self.nodes:
            if n.pos == pos:
                return n
        return None
            

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
    def __init__(self, src, dest, cls='draw', label=None, labelpos=None, startface=None):
        self.src = src
        self.dest = dest
        self.cls = cls
        self.label = label
        self.labelpos = labelpos
        self.startface = startface
        self.leg = '--'
        self.route = ''
