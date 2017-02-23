`ifdef A1
// branch a
assign a = aa;
`elsif B1
// branch b
assign b = bb;
`else C1
// branch c
assign c = cc;
`endif
module m(
`ifdef A1
input aa,
output a,
`elsif B1
input bb,
output b,
`else C1
input cc,
output c,
`endif
);
`ifdef A1
// branch a
assign a = aa;
 `elsif B1
// branch b
assign b = bb;
`else C1
// branch c
assign c = cc;
`endif
endmodule