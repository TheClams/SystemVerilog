unique case (cstate)
	SLAVE0  : begin
		mode = 0;
		done_o = 0;
	end
	default : begin
		mode = done_mode_i;
		done_o = 1;
	end
endcase