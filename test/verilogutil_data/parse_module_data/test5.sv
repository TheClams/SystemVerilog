module m1 (

input wire [1:5] a7, aa7,
output wire [1:5] b7, bb7,
inout wire [1:5] c7, cc7,

input reg [1:5] a8, aa8,
output reg [1:5] b8, bb8,
inout reg [1:5] c8, cc8,

input  wire signed a10, aa10,
output wire signed b10, bb10,
inout wire signed c10, cc10,

input  wire unsigned a11, aa11,
output wire unsigned b11, bb11,
inout wire unsigned c11, cc11,

output reg dump
);

logic toto[4],b[5];

endmodule
