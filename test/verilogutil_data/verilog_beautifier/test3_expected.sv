//------------------------------------------------------------------------------
// Copyright (c)
// confidential. All rights reserved
/*------------------------------------------------------------------------------
//
// Module: my_module
//  Test module for beautifier => bad indentation everywhere
//
//----------------------------------------------------------------------------*/

module my_module (
   input                      clk    , // Clock
   input  logic               clk_en , // Clock Enable
   input                      rst_n  , // Asynchronous reset active low;
   my_interface.master        my_if  , // interface
   input  my_pkg::my_type_in  din    ,
   input        [ 7:0]        ctrl   , // Control
                                       // Multiline comment about control
   output reg   [15:0]        testbus,
   // spliting comment
   output my_pkg::my_type_out dout     // output data
);


/*------------------------------------------------------------------------------
--  Test signal declaration
------------------------------------------------------------------------------*/
   logic [ 3:0] cnt ; // counter
   logic [15:0] test; // tests comment

   reg   [ 4:0]    reg0 ;
   logic [15:0]    t1,t2,t3;
   my_pkg::my_type data0;


//------------------------------------------------------------------------------
//  Process alignment
//------------------------------------------------------------------------------

   always_ff @(posedge clk or negedge rst_n)
      if(~rst_n)
         dout <= 0;
      else if(clk_en) begin
         dout    <= ~dout;
         testbus <= ctrl[3:0];
      end

   // case align
   always_comb begin : proc_comb
      case(my_if.sel)
         16 : test = din[16]; // blabla
         7  : test = din[7];
         3  : begin
            case(cnt[1:0])
               0       : test = 4'h0;
               1       : test = 5 + test; // test
               2       : test = 6 - test;// blabl
               default : test = test[0] ? test : 4'b0000;
            endcase
         end
         4 :
            if(test) begin
               test = test - 1;
            end else begin
               test = cnt;
            end
         default : test = ctrl; // default case
      endcase
   end

   // test more indentation level
   always_ff @(posedge rst_n ) begin : proc_
      if(clk) begin
         test    <= 0;
         testbus <= 0;
         cnt     <= 4'h0;
      end else begin
         if(clk_en)
            if(test[0])
               if(test[1]) begin
                  cnt <= 0;
                  if(test[2])
                     cnt <= 4'h2; // splitception o0
               end
         else begin
            testbus <= cnt;
            if(cnt[16])
               cnt <= cnt + 1;
         end
      end
   end

// Test module instantiation with and without param
   my_submodule i_sub (
      .i0         (din                ),
      .in1        (my_pkg::test'(ctrl)),
      .clk_en     (clk_en             ),
      .output_data(test               )
   );


// test split statement: align on ( or =
   always @(ctrl, test, din, my_if.field0,
         cnt,  my_if.field1, dout)
      // line Comment
      testbus = ((ctrl[0] == 1'b1) && my_if.field0) ? my_pkg::testbus_value0    :
         ((ctrl[1] == 1'b1) && my_if.field1) ? my_pkg::testbus_value1    :
         ((ctrl[2] == 1'b1) && dout[4]) ? cnt    :
         my_pkg::testbus_default                           ;

   assign test = ctrl[7:0]; // assign_comment
   assign cnt  = test + 4;

   assign testbus = {cnt,test};

   my_param_submodule #(.PARAM0(1), .P4(my_pkg::P4)) i_param_sub (.input_0(din[1:0]), .in1(ctrl[7:0]), .clk_en(clk_en), .output_data(cnt[15:10]));

   // Function: abs
   // Returns absolute value of integer
   function integer abs(input integer value);
      if (value >=0 ) begin
         return value;
      end
      else
         return -value;
   endfunction : abs

   class testclass;
   endclass

endmodule