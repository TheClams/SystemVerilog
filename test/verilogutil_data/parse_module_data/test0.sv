module test #(
    pq_channels = 10
    )(
    input [pq_channels-1:0][1:0] k,
    input i_rx [1:pq_channels],
    output o_tx [1:pq_channels]
    );

    always_comb a = b;

endmodule