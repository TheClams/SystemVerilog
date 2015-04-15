    always @(posedge i_clk)
        if(i_rst) begin
            a <= 0;
        end

    logic        rst      ;
    logic [23:0] cmi_count;
    logic        marker_st;