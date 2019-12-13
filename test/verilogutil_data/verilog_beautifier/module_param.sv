module example #(
    parameter FOO = 2,
    parameter BAR = 4,
    localparam FOO_BAR = my_func(FOO, BAR, 5),
) (
    input logic clk,
    input logic [FOO-1:0] data_in,
    output logic [FOO_BAR-1:0] data_out
);