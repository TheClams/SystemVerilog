module m3();
generate
genvar inst;
for(inst=0; inst<pq_console; inst++) begin
m1 m1e (.clk(clk));
m2 m2e (.clk(clk));
end
endgenerate
endmodule