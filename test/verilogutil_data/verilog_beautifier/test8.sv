module test import foo_pkg::*; (
input  logic i_en,
output logic [pq_symbols*4-1:0] o_all_symbols_4b,
input  logic i_en2
);
endmodule

module test_2
import foo1_pkg::*;
import foo2_pkg::*;
(
input logic i_en ,
input logic i_en2
);
endmodule