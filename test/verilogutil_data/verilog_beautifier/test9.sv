always_comb begin
case (state)
st_load_crc0,
st_wait_load_crc0,
st_load_crc1,
st_wait_load_crc1 : begin
sym_4b   = crc;
load_sym = load_crc_str;
end
default : begin
sym_4b   = i_sym_4b;
load_sym = i_load_sym_4b_str;
end
endcase
end