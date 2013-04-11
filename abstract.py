

class Graph(object):
    def __init__(self, stylesheet):
        self.styles = stylesheet
        self.nodes = []
        self.edges = []

    def add(self, obj):
        if isinstance(obj, GraphNode):
            self.nodes.append(obj)
            obj.set_num(len(self.nodes)-1)
        elif isinstance(obj, GraphEdge):
            self.edges.append(obj)

    def emit_simple_node_matrix(self, numperrow=1):
        calculated_style = self.styles.get(elem="matrix")
        print r"\matrix["+calculated_style+r"] {"
        self.styles.push(elem="matrix")
        for num, n in enumerate(self.nodes):
            n.emit(self.styles)
            if (num+1) % numperrow == 0 or num == len(self.nodes)-1:
                print r"\\"
            else:
                print r"&"
        print r"};"
        self.styles.pop()

    def emit_node_matrix(self):
        self.normalise_node_coords()
        calculated_style = self.styles.get(elem="matrix")
        print r"\matrix["+calculated_style+r"] {"
        self.styles.push(elem="matrix")
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
                        posdict[poskey].emit(self.styles)
                    if x<xmax:
                        print " & ",
                print r"\\"
        else:
            print r"  %no nodes"
        print r"};"
        self.styles.pop()
    
    def emit_edge_paths(self):
        for e in self.edges:
            path_style = self.styles.get(elem='path', cls=e.cls, override=e.style)
            edgelabel_style = self.styles.get(elem='node', cls='edgelabel', content=e.label, override=e.labelpos)
            posstr = '[%s]'%edgelabel_style
            labelstr = 'node%s{%s}'%(posstr, e.label) if e.label else ''
            startface = '.%s'%e.startface if e.startface!=None else ''
            print r"\path[%s] (%s%s) %s %s %s (%s);" % (path_style, e.src, startface, e.leg, labelstr, e.route, e.dest)
        
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
        self.styles.push(elem="chain")
        nprev = None
        for num, n in enumerate(self.nodes):
            fromme = self.edges_from(num)
            tome = self.edges_to(num)
            if not tome:
                print r"\chainin ("+self.node_ident(num)+r");"
            else:
                for s in tome:
                    if s.src == nprev:
                        path_style = self.styles.get(elem="path", override=s.style)
                        print r"\chainin ("+self.node_ident(num)+r") [join=by {"+path_style+r"}];"

            nprev = num
        print r"};"
        self.styles.pop()

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
    def __init__(self, name, cls='', ident=None, num=-1, pos=None, style=''):
        self.pos = pos
        self.name = name
        self.cls = cls
        self.style = style
        self.num = num
        self.ident = "n%s"%num if ident == None else ident

    def emit(self, styleset):
        calculated_style = styleset.get(elem="node", cls=self.cls, ident=str(self.ident), content=self.name, override=self.style)
        print r"\node["+calculated_style+r"] ("+str(self.ident)+r") {"+self.name+r"};",

    def set_num(self, num):
        if self.ident == "n%s"%self.num:
            self.ident = "n%s"%num
        self.num = num
        

class GraphEdge():
    def __init__(self, src, dest, cls='', label=None, labelpos=None, startface=None, style=''):
        self.src = src
        self.dest = dest
        self.cls = cls
        self.style = style
        self.label = label
        self.labelpos = labelpos
        self.startface = startface
        self.leg = '--'
        self.route = ''
