ID: '\w+';
WS: '[ \t]+' (%ignore);
DOWN_EDGE: '\|';

start: bin_edge;
?bin_edge: (bin_edge DOWN_EDGE)? nod;
nod: ID;