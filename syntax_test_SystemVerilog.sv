// SYNTAX TEST "SystemVerilog.sublime-syntax"

`define my_macro ;
// <- constant.other.preprocessor
//      ^ entity.name.type.define
`my_macro
// <- constant.other.define
logic x;
/*------------------------------------------------------------------------------
--  Test interface definition with modport
------------------------------------------------------------------------------*/

interface my_interface1;
// <- keyword.control
//        ^ entity.name.type.class
    logic   one;
//  ^ storage.type
    logic   two;

    modport sys (
//  ^ keyword.control
//          ^ support.function.generic
        input one,
//      ^ support.type
        output two
//      ^ support.type
    );
endinterface /* my_interface1 */
// <- keyword.control
//           ^ comment.block

    // Interface with indentation
    interface my_interface2;
//  ^ keyword.control
//            ^ entity.name.type.class
        logic   one;
        logic   two;

        modport sys (
            inout one,
//          ^ support.type
            output two
        );

    endinterface

/*------------------------------------------------------------------------------
--  Typedef
------------------------------------------------------------------------------*/
typedef logic [31:0] queue_of_levels [$];
// <- keyword.control
//      ^ storage.type
//             ^ constant.numeric.decimal
//               ^ keyword.operator
//                   ^ entity.name.type
//                                    ^ keyword.operator

    typedef my_module#(16)  t_my_module_16;
//  ^ keyword.control
//          ^ storage.type
//                   ^ keyword.operator
//                     ^ constant.numeric.decimal
//                          ^ entity.name.type

    typedef logic[7:0]  t_byte;
//  ^ keyword.control
//          ^ storage.type
//                ^ constant.numeric.decimal
//                 ^ keyword.operator
//                      ^ entity.name.type


/*------------------------------------------------------------------------------
--  Module declaration
------------------------------------------------------------------------------*/

module my_module
// <- keyword.control
//     ^ entity.name.type
    import my_pkg::*;
//  ^ keyword.control
//         ^ support.type.scope
//               ^ keyword.operator.scope
//                 ^ keyword.operator
  #(parameter int P1=0,
//^ keyword.operator
//  ^ keyword.other
//            ^ storage.type
//                ^ constant.other.net
    logic [15:0] P2 = 16'b0000_1111,
//               ^ constant.other.net
//                    ^ constant.numeric
//                            ^ constant.numeric
    real P3 = my_pkg::pp,
//  ^ storage.type
//            ^ support.type
    )
  (
    my_interface1.sys   if1,
//  ^ storage.type.interface
//                ^ support.modport
    my_interface2       if2, // Comment if2
//  ^ storage.type.userdefined
//                           ^ comment.line
    input var  logic    clk, /* comment clk */
//  ^ support.type
//        ^ storage.type
//              ^ storage.type
//                           ^ comment.block
    input wire my_pkg::my_type din,
//        ^ storage.type
//             ^ support.type.scope
//                     ^ storage.type

    output  wire        my_out
  );

wire my_pkg::my_type data;
// <- storage.type
//   ^ support.type.scope
//           ^ storage.type


    timeunit 1ns;
//  ^ keyword.control
//           ^ constant.numeric.time
timeprecision 1fs;
// <- keyword.control
//            ^ constant.numeric.time

/*------------------------------------------------------------------------------
--  User Defined type
------------------------------------------------------------------------------*/
    t_byte  b0, // Comments
//  ^ storage.type.userdefined
            b1;
local t_byte b2 = 8'hFF;
// <- keyword.other
//    ^ storage.type.userdefined
//              ^ keyword.operator
//                ^ constant.numeric

mytype [3:0][4][`MACRO*4] myvar3[PARAM-1:`TEST/4]; // userdefined type with packed/unpacked
// <- storage.type.userdefined

logic [3:0]  sig_logic = 4'shC;

/*------------------------------------------------------------------------------
--  PSL
------------------------------------------------------------------------------*/
// psl a_mypsl_assert: assert never {sig_logic!=4'hX};
// <- meta.psl

/*------------------------------------------------------------------------------
--  Instantiation of interface, module
------------------------------------------------------------------------------*/
my_interface1#(1) if1(clk,rst_n);
    virtual my_interface1#(3,4) if2;

my_module i_my_module
  (
    .if1(if1),
    .if2(if2),
    .clk(`MYMACRO(5).clk),
//   ^ support.function.port
//        ^ constant.other.define
//                   ^ -support.function.port
    .my_out(my_out),
  );

parameter
    my_module.test_param = 23'h44;

localparam mytype myvar = mytype'(MY_INIT/4+8);
localparam myvar1 = MY_INIT1;
localparam logic [1:0] myvar2 = MY_INIT2;

/*------------------------------------------------------------------------------
--  Structure / Typedef
------------------------------------------------------------------------------*/
typedef struct {logic a; int b; bit [3:0] c;} mystruct;
protected const mystruct c_var = '{a:0,b:1,c:4'hD};
//                                 ^ support.function.field

/*------------------------------------------------------------------------------
--  Task & functions
------------------------------------------------------------------------------*/

task connect(virtual nfc_ip_top_if dut_if);
// <- keyword.control
//   ^ entity.name.function
//           ^ keyword.other
//                   ^ storage.type
endtask


function void my_pkg::my_func(ref logic d, input int din,
//            ^ support.type.scope.systemverilog
//                  ^ keyword.operator.scope.systemverilog
                      input bit[3:0] d,
                      output bit[$clog(kk)-1:0] d2,
//                               ^ support.function.systemverilog
                      output dout);
    $display("d=%0d",d);
endfunction : my_func

        function automatic integer CLOGB2;
        endfunction

/*------------------------------------------------------------------------------
--  Invalid syntax
------------------------------------------------------------------------------*/
(])) [)]]
// <- -invalid.illegal
 // <- invalid.illegal
  // <- -invalid.illegal
   // <- invalid.illegal
     // <- -invalid.illegal
      // <- invalid.illegal
       // <- -invalid.illegal
        // <- invalid.illegal

/*------------------------------------------------------------------------------
--  MISC
------------------------------------------------------------------------------*/

   nettype t_mytype mytype with myresolve;
// ^ keyword.control
//         ^ storage.type
//                  ^ entity.name.type
//                         ^ keyword.control
//                              ^ support.function.resolve


fork
join_any

fork : f_label
    begin : b_label

    end : b_label
join : f_label

covergroup cg @(e);
    option.per_instance = 1;
    cp : coverpoint cp_name {
        bins b01    = {[0:1]};
        bins b23    = {[2:3]};
        bins others = default;
        option.comment = "comment";
        option.at_least = 1_000; //
    }
endgroup

always_ff @(posedge clk or negedge rst_n) begin : proc_
    if (~rst_n)
        a <= '0;
    else if (en)
        a <= a + b;
end


generate
    for (int i = 0; i < count; i++) begin
        some #(1,2,3) i (
            .a(a),
            b,
            c
        );
    end
endgenerate

