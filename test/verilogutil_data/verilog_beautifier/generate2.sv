generate
if(PARA1)
begin : gen_1
always @ (posedge clk)
begin
a <= c;
end
always @ (posedge clk)
begin
c <= d;
end
end
endgenerate

generate
for (g=0;g<10;g=g+1)
begin : gen_loop
always @ (posedge clk)
begin
a[g] <= c[g];
end
always @ (posedge clk)
begin
c[g] <= d[g];
end
end
endgenerate

generate
if(PARA1)
begin : gen_1
test_mod u_inst (
.clk (clk ),
.rst (rst ),
.din (din ),
.dout(dout)
);
end
endgenerate

generate
begin
for(h=0;h<10;h=h+1)
begin : gen_1
for (g=0;g<10;g=g+1)
begin : gen_loop
always @ (posedge clk)
begin
a[h][g] <= b[g][h];
end
end
end
end
endgenerate