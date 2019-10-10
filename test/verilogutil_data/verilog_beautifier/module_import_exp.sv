module data_import (
   input  logic RST_n,
   input  logic CLK  ,
   input  logic DIN  ,
   output logic DOUT
);

   // Dummy logic
   always_ff @(posedge CLK, negedge RST_n) begin
      if (!RST_n) begin
         DOUT <= '0;
      end else begin
         DOUT <= DIN;
      end
   end

endmodule