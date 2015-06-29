module v_comments ( a,
b,
c,
d, d1, d2, d3 );
input a;
inout [10:0] b;
output [0:10] c;
output [ ((2*32) - 1) : 0 ] d;
output [ 32 : 0 ] d1;
output [ ( MATH - 1 ): 0 ] d2;
output [ 32 - 1: 0 ] d3;
reg           d;
reg [11:0]    e;
endmodule