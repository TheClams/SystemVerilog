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
// <- keyword.other
//        ^ entity.name.type.class
    logic   one;
//  ^ storage.type
    logic   two;

    modport sys (
//  ^ keyword.modport
//          ^ entity.name.modport
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
//  ^ keyword.other
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

sequence e3(sequence a, untyped b);
@(posedge sysclk) a.triggered ##1 b;
endsequence

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

interconnect [0:1] iBus;
// <- storage.type.systemverilog
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
--  Coverage
------------------------------------------------------------------------------*/
covergroup cg @(posedge e);
// <- meta.block.cover.systemverilog keyword.other.systemverilog
//         ^^ meta.block.cover.systemverilog entity.name.type.covergroup.systemverilog
//              ^^^^^^^ meta.block.cover.systemverilog keyword.other.systemverilog

    option.per_instance = 1;
//         ^^^^^^^^^^^^ meta.block.cover.systemverilog variable.other.systemverilog
    cp0 : coverpoint cp_name {
//  ^^^ meta.block.cover.systemverilog entity.name.type.coverpoint.systemverilog
        bins b01    = {[0:1]};
        bins b23    = {[2:3]};
        bins apple = X with (a+b < 257) matches 127
//                                      ^^^^^^^ meta.block.cover.systemverilog keyword.other.systemverilog
        bins others = default;
        option.comment = "comment";
        option.at_least = 1_000; //
    }

    cp0 : coverpoint (this.vif.sig && this.vif.en) iff(cmd.kind == ANVM_CMD_abort) {
//                                                 ^ keyword.other
        illegal_bins il_bins = default;
//      ^^^^^^^^^^^^ keyword.other.systemverilog
//                             ^^^^^^^ keyword.other.systemverilog
        wildcard bins b_data_super_queue = {2'b1?};
//      ^^^^^^^^ keyword.other.systemverilog
        ignore_bins ig_bins = {3} ;
//      ^^^^^^^^ keyword.other.systemverilog
    }

    cx : cross cp0, cp1 iff(rst_n){
//                      ^^^ keyword
        bins w_11 =  ! binsof(a) intersect {[100:200]};
//      ^^^^ keyword.other.systemverilog
//                     ^^^^^^ meta.block.cover.systemverilog keyword.other.systemverilog
//                               ^^^^^^^^^ meta.block.cover.systemverilog keyword.other.systemverilog
        bins allother = default sequence ;
//                              ^^^^^^^^ meta.block.cover.systemverilog keyword.other.systemverilog
    option.detect_overlap = 1;
    }

endgroup

covergroup x (int nsid, input conf cfg, ref logic z) with function sample(int slba);
//                      ^^^^^ meta.block.cover.systemverilog support.type.systemverilog
//                                                   ^^^^^^^^^^^^^^^^^^^ meta.block.cover.systemverilog keyword.other.systemverilog
    type_option.strobe = 1;
    a : coverpoint slba {
       bins range[3] = {[32'h0000_0000 : cfg.num_ns[nsid].ns_size]};
//                       ^^^^^^^^^^^^^ meta.block.cover.systemverilog constant.numeric.systemverilog
       bins mod3[] = {[0:255]} with (item % 3 == 0)
//                             ^^^^ meta.block.cover.systemverilog keyword.other.systemverilog
    }
endgroup
// <- meta.block.cover.systemverilog meta.object.end.systemverilog keyword.control.systemverilog

    covergroup cg1;
//  ^^^^^^^^^^ meta.block.cover.systemverilog keyword.other.systemverilog
    endgroup // cg1
//  ^ meta.block.cover.systemverilog meta.object.end.systemverilog keyword.control.systemverilog

/*------------------------------------------------------------------------------
--  Constraint
------------------------------------------------------------------------------*/

constraint constraint_c {
// <- keyword.other
//         ^ entity.name
    solve y before x;
//  ^^^^^ meta.block.constraint.systemverilog keyword.other.systemverilog
//          ^^^^^^ meta.block.constraint.systemverilog keyword.other.systemverilog
    soft var_1 < 1;
//  ^ keyword.other
    x dist { [100:102] := 1, 200 := 2, 300 :/ 5};
//    ^^^^ meta.block.constraint.systemverilog keyword.other.systemverilog
    if (mode == little)
//  ^^ meta.block.constraint.systemverilog keyword.other.systemverilog
        len < 10;
    else if (mode == big)
        len > 100;
    length == count_ones( v ) ;
//            ^^^^^^^^^^ meta.block.constraint.systemverilog support.function.generic.systemverilog
}

constraint C::proto1 { x inside {-4, 5, [y:2*y]}; }
//         ^ meta.block.constraint.systemverilog storage.type.userdefined.systemverilog
//          ^^ keyword.operator.scope.systemverilog
//            ^^^^^^ meta.block.constraint.systemverilog entity.name.section.systemverilog
//                       ^^^^^^ meta.block.constraint.systemverilog keyword.other.systemverilog
//                                ^ meta.block.constraint.systemverilog meta.brackets.systemverilog constant.numeric.decimal.systemverilog
//                                          ^ meta.block.constraint.systemverilog meta.brackets.systemverilog keyword.operator.arithmetic.systemverilog
//                                             ^ meta.brackets.systemverilog keyword.operator.array.end.systemverilog

p.randomize() with { length inside [512:1512]; mode dist {1:=4, [2:3]:/3} ;}
// ^^^^^^^^ support.function.generic.systemverilog
//                 ^ meta.block.constraint.systemverilog punctuation.section.block.begin.systemverilog
//                          ^^^^^^ keyword.other.systemverilog
//                                                                         ^ punctuation.section.block.end.systemverilog

assert(a.randomize(ack) with {}; );

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

checker op_test (logic clk, vld_1, vld_2, logic [3:0] opcode);
    bit [3:0] opcode_d1;
    always_ff @(posedge clk) opcode_d1 <= opcode;
    covergroup cg_op with function sample(bit [3:0] opcode_d1);
        cp_op : coverpoint opcode_d1;
    endgroup: cg_op
    cg_op cg_op_1 = new();
    sequence  op_accept;
//  ^ keyword.control
//            ^ entity.name.function
        @(posedge clk) vld_1 ##1 (vld2, cg_op_1.sample(opcode_d1));
    endsequence
    cover property (op_accept);
endchecker


program automatic test (
// <- keyword.other.systemverilog
//      ^^^^^^^^^ keyword.other.systemverilog
//                ^^^^ entity.name.type.program.systemverilog
    dut_interface.test_ports axi_dut
//  ^^^^^^^^^^^^^ meta.program.systemverilog storage.type.interface.systemverilog
//                ^^^^^^^^^^ support.modport.systemverilog
);
endprogram: test
//          ^^^^ entity.label.systemverilog


package automatic example_pkg;
//      ^^^^^^^^^ meta.definition.systemverilog keyword.other.systemverilog
//                ^^^^^^^^^^^ meta.definition.systemverilog entity.name.type.class.systemverilog
endpackage : example_pkg