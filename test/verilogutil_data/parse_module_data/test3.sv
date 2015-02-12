module m1 (
input wire a1, aa1,
output wire b1, bb1,
inout wire c2, cc2,

input reg a2, aa2,
output reg b2, bb2,
inout reg c2, cc2,

input wire [1:0] a4, aa4, aaa4,
output wire [1:0] b4, bb4, bbb4, bbbb4,
inout wire [1:0] c4, cc4, ccc4, cccc4, ccccc4,

input reg [1:0] a5, aa5,
output reg [1:0] b5, bb5,
inout reg [1:0] c5, cc5,

input wire [1:5] a7, aa7,
output wire [1:5] b7, bb7,
inout wire [1:5] c7, cc7,

input reg [1:5] a8, aa8,
output reg [1:5] b8, bb8,
inout reg [1:5] c8, cc8,



output reg dump
);

endmodule
