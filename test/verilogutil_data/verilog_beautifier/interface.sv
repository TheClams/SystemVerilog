interface uvm_if (input logic clk, input logic rstn);

    logic rst_n;
    modport monitor_mp (input clk, input rst_n);

endinterface