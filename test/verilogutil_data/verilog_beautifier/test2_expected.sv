module m ();
    logic a;
    always @(posedge clk)
        ping <= pong;
endmodule