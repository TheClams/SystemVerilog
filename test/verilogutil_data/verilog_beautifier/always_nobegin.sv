always @(posedge clk, negedge rst_n)
if (~rst_)
cnt <= 0;
else if (init)
cnt <= 1;
else if (cnt == max)
cnt <= 6'd0;
else
cnt <= cnt + 1;