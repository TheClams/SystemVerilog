module mux #(
parameter logic [1:0] pq_ports = 2,
parameter integer pw_data  = 8,
parameter logic [pw_data-1:0][pq_ports-1] p_array  = '0
) (
input  logic [pw_data-1:0][0:pq_ports-1] i_datas,
output logic [$clog2(pq_ports+1)-1:0] o_port_num,
input  logic [pw_data-1:0] i_data [0:pq_ports-1]
);

logic   [1:0] pq_ports;
logic [pw_data-1:0][pq_ports-1] p_array;

endmodule // mux