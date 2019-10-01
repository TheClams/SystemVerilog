modport bus_master (
   output req, ack,
   output data_master,
   input  data_slave,
   input  ready,
   input  clk, rst,
   import task parity_check(packet_t data),
   import function logic parity_gen(packet_t data)
);