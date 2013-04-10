from plyplus import Grammar, STree, SVisitor, STransformer, is_stree

	
class Style(object):

	stylesheet_grammar = Grammar(r"""
		WS: '[ \t\f]+' (%ignore);
		NL: '\n' (%newline) (%ignore);
		
		ID: '\w+';
		BODY: '\[[^\]]*\]';
		PCLS: '\.';
		PID: '\#';
		PCONT: '=';
		
		start: rule*;
		rule: selector_list body;
		selector_list: selector (',' selector)*;
		selector: selector_stage+;
		selector_stage:	elem (PCLS cls | PID ident| PCONT content)* | (PCLS cls | PID ident | PCONT content)+;
		elem: ID;
		cls: ID;
		ident: ID;
		content: ID;
		body: BODY;
		"""
	)
	
	def __init__(self, stylestring):
		self.stack = [{'elem':'all'}]
		self.style_rules = []
		
		#Parse style sheet
		#for t in Style.stylesheet_grammar.lex(stylestring):
		#	print "line {0.lineno:<3}col {0.lexpos:<4}{0.type}:\t{0.value}".format(t)
		tree = Style.stylesheet_grammar.parse(stylestring)
		#tree.to_png_with_pydot("styleAST.png")
		
		#Process styles
		for rule in tree.select("rule"):
			body = rule.child("body").child()[1:-1].strip(", \t\n\r")
			for selector in rule.select("selector"):
				template = []
				specificity = 0
				for stage in selector.children("selector_stage"):
					template_row = {}
					for matcher in stage.select("/elem|cls|ident|content/"):
						if matcher.head not in template_row:
							template_row[matcher.head] = str(matcher.tail[0])
						elif type(template_row[matcher.head]) == list:
							template_row[matcher.head].append(str(matcher.tail[0]))
						else:
							template_row[matcher.head] = [template_row[matcher.head], str(matcher.tail[0])]
						specificity += {'elem': 1, 'cls': 1<<8, 'content': 1<<16, 'ident': 1<<24}[matcher.head]
					template.append(template_row)
				self.style_rules.append((specificity, template, body))
				
		self.style_rules.sort(key=lambda t: t[0])
		#print "Processed style rules:\n%s"%(self.style_rules)
	
	def get(self, **params):
		styles = []
		for rule in self.style_rules:
			template = list(rule[1])
			state = list(self.stack)
			state.append(params)
			match_template = True
			template.reverse()
			for trownum, trow in enumerate(template):
				match_row = False
				while len(state):
					level = state.pop()
					match = True
					for key, item in trow.items(): #match template row to element?
						if key not in level:
							match = False
							break #for
						if type(level[key]) is list:
							if type(item) is list:
								if frozenset(item) > frozenset(level[key]):
									match = False
									break #for
							else:
								if item not in level[key]:
									match = False
									break #for
						else:
							if type(item) is list or level[key] != item:
								match = False
								break #for
					if match: #item matched on this level
						match_row = True
						break #while
					if trownum == 0: #was expecting to find first immediately: fail.
						break #while
				if not match_row: #
					match_template = False
					break #for trow
					
			if match_template and rule[2] not in styles:
				styles.append(rule[2])
		return ', '.join(styles)
	
	def push(self, **params):
		return self.stack.append(params)
	
	def pop(self):
		return self.stack.pop()