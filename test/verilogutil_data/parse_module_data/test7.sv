module a #(
	a1 = 1_000,
	a2 = a1*3,
	logic [15:0] a3 = a1*a2,
	a4 = a2-a1, // Comment 1
	a5 = a1+a2,
	uint a6 = (a1+a2)*2  ,  /* Comment 2*/
	a7 = (a1+a2)+a3 ,
	a8 = a2/a1,
	a9 = a2 >>> 1,
	a10 = a2 <<< a1
	)(

	);
endmodule
