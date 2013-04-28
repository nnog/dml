

class Graph(object):
    def __init__(self, styles):
        """Instantiate graph object with a reference to <styles> Style object"""
        self.styles = styles
        self.nodes = []
        self.edges = []

    def add(self, obj):
        if isinstance(obj, GraphNode):
            self.nodes.append(obj)
            obj.set_num(len(self.nodes)-1)
        elif isinstance(obj, GraphEdge):
            self.edges.append(obj)

    def emit_simple_node_matrix(self, numperrow=1):
        """Emit a matrix of nodes going horizontal then breaking onto new line every <numperrow> nodes"""
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
        """Emit a matrix of nodes using integer pos[x,y] values to determine cell location of each"""
        self.normalise_node_coords()
        calculated_style = self.styles.get(elem="matrix")
        print r"\matrix["+calculated_style+r"] {"
        self.styles.push(elem="matrix")
        if len(self.nodes) >= 1:
            posdict = {}
            xmax = float('-inf')
            ymax = float('-inf')
            for n in self.nodes:
                posdict[repr((int(n.pos[0]), int(n.pos[1])))] = n
                xmax = max(xmax, n.pos[0])
                ymax = max(ymax, n.pos[1])

            for y in range(int(ymax+1)):
                for x in range(int(xmax+1)):
                    poskey = repr((x,y))
                    if poskey in posdict:
                        posdict[poskey].emit(self.styles)
                    if x<xmax:
                        print " & ",
                print r"\\"
        else:
            print r"  %no nodes"
        print r"};"
        self.styles.pop()
        
    def emit_nodes_abs(self):
        """Emit \node's with absolute positions"""
        for n in self.nodes:
            n.emit(self.styles, atpos=True)
            print
    
    def emit_edge_paths(self):
        """Emit edges as \path's with labels and any routing that has been calculated"""
        for e in self.edges:
            path_style = self.styles.get(elem='path', cls=e.cls, override=e.style)
            self.styles.push(elem='path', cls=e.cls)
            edgelabel_style = self.styles.get(elem='node', cls='edgelabel', content=e.label, override=e.labelpos)
            posstr = '[%s]'%edgelabel_style
            labelstr = 'node%s{%s}'%(posstr, e.label) if e.label else ''
            startface = '.%s'%e.startface if e.startface!=None else ''
            if e.src == e.dest: #self loop
                legstr = "edge[%s]"%self.styles.get(elem='edge', cls='loop', underride='loop '+(e.labelpos if e.labelpos else 'above'))
            else:
                legstr = e.leg
            print r"\path[%s] (%s%s) %s %s %s (%s);" % (path_style, e.src, startface, legstr, labelstr, e.route, e.dest)
            self.styles.pop()
        
    def route_edges(self):
        """In a grid fashion, attempt to reroute edges around other occupied cells in matrix"""
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
                    
    def layout(self, type='digraph', alg='neato', sep=4, shape='ellipse', w=1.5, h=1, startangle=0):
        """Use PyDOT to access GraphViz layout programs."""
        import pydot
        g = pydot.Dot(graph_type=type, normalize=startangle, sep=sep)
        for i, n in enumerate(self.nodes):
            g.add_node(pydot.Node(n.ident, width=w+len(n.name)/50, height=h+len(n.name)/50, shape=shape, root=(i==0)))
        for e in self.edges:
            g.add_edge(pydot.Edge(e.src, e.dest))
            
        g_pos = pydot.graph_from_dot_data(g.create_dot(prog=alg))
        for n in self.nodes: #grab node positions
            x,y = g_pos.get_node(n.ident)[0].get_pos().strip('"').split(',', 1)
            n.pos = (float(x),float(y))
        self.scale_node_coords({'dot':0.025, 'neato':0.05, 'sfdp':0.075, 'fdp':0.0075, 'circo':0.02}.pop(alg, 0.05))
    
    def normalise_node_coords(self):
        if len(self.nodes) == 0: return
        xmin = ymin = float('inf')
        for n in self.nodes:
            xmin = min(xmin, n.pos[0])
            ymin = min(ymin, n.pos[1])
        for n in self.nodes:
            n.pos = (round(n.pos[0]-xmin,2), round(n.pos[1]-ymin,2))
            
    def scale_node_coords(self, scale):
        if isinstance(scale, (tuple, list)):
            xscale = scale[0]
            yscale = scale[1]
        else:
            xscale = scale
            yscale = scale
            
        for n in self.nodes:
            n.pos = (round(n.pos[0]*xscale,2), round(n.pos[1]*yscale,2))

    def flip_layout(self, flipdir = (-1 , 1)):
        self.scale_node_coords(flipdir)
        self.normalise_node_coords()

    def auto_flip_layout(self):
        """Attempt to get start node left-top-most"""
        if len(self.nodes) == 0 or len(self.start_nodes()) == 0:
            return

        startnode = self.start_nodes()[0]

        xmax = ymax = float('-inf')
        for n in self.nodes:
            xmax = max(xmax, n.pos[0])
            ymax = max(ymax, n.pos[1])

        if startnode.pos[0] == xmax:
            self.flip_layout((-1, 1))
        if startnode.pos[1] == ymax:
            self.flip_layout((1, -1))
        
        

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
    
    def start_nodes(self):
        return [n for n in self.nodes if len(self.edges_to(n.ident))==0]
    
    def end_nodes(self):
        return [n for n in self.nodes if len(self.edges_from(n.ident))==0]

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

    def emit(self, styleset, atpos=False):
        calculated_style = styleset.get(elem="node", cls=self.cls, ident=str(self.ident), content=self.name, override=self.style)
        print r"\node["+calculated_style+r"] ("+str(self.ident)+r") "+("at %s "%repr(self.pos) if atpos else '')+r"{"+self.name+r"};",

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
