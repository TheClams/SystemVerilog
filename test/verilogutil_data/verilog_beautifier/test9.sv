always_comb begin
case (state)
st_load_crc0,
st_wait_load_crc0,
st_load_crc1, // State CRC1
st_wait_load_crc1 : begin
sym_4b   = crc;
load_sym = load_crc_str;
end
st_idle :
sym_4b   = 0;
default : begin
sym_4b   = i_sym_4b;
load_sym = i_load_sym_4b_str;
end
endcase
end

always @(posedge clk) begin
   if(state==st_idle)
   case(sym_4b)
   endcase
   if(state==st_load_crc0)
      case(crc)
      endcase
end