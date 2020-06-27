module decoder
  import definitions_pkg::*;
  (output opcode_set_t       opcode,
   input  instruction_set_t  instruction
  );
  timeunit 1ns/1ns;

endmodule : decoder