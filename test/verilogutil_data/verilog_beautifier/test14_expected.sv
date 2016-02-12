module mux #(
    pq_ports = 2,
    pw_data  = 8
) (
    output logic [$clog2(pq_ports+1)-1:0] o_port_num           ,
    input  logic [           pw_data-1:0] i_data [0:pq_ports-1]
);

endmodule // mux