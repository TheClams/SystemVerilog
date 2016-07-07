module mux #(
   pq_ports = 2,
   pw_data  = 8
) (
   output logic        [$clog2(pq_ports+1)-1:0] o_port_num               ,
   input        signed [           pw_data-1:0] i_data     [0:pq_ports-1],
   input               [                   3:0] i_data_mod [0:pq_ports-1][2]
);

endmodule // mux