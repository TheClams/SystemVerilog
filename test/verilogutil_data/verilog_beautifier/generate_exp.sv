module tb ();

   generate
      if(x) begin : gen_x
         assign x = 1;
      end else begin : gen_no_x
         assign x = 0;
      end
   endgenerate

/*
*/
   assign y = 2;
   assign z = 3;

endmodule
