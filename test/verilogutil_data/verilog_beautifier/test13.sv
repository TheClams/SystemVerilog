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
module m();
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