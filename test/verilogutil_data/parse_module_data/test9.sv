module arithm_op_port #(
	pq_symbols = 4
	)(
	output logic [(pq_symbols<<1)-1:0] name3,
	output logic [(pq_symbols>>1)-1:0] name2,
	output logic [(pq_symbols*4/2)-1:0] name1,
	output logic [pq_symbols*4-1:0] name
	);
endmodule