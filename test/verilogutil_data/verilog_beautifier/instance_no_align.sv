blk_type #(
    .WIDTH(WIDTH),
    .LATENCY(LATENCY)
) blk_inst (
    .y(y),
    .enableY(enableY),
    .x(x),
    .init(init),
    .enable(enable),
    .clock,
    .resetAsync
);