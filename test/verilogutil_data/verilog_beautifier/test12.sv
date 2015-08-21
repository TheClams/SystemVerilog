module m3();
generate
genvar inst;
for(inst=0; inst<pq_console; inst++) begin

m2 m2e (.clk(clk));
end
endgenerate
endmodule