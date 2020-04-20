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
            output two,
            input  clk, rst,

            import task parity_check(packet_t data) ,
//          ^^^^^^ keyword.other.systemverilog
//                 ^^^^ keyword.other.systemverilog
//                      ^^^^^^^^^^^^ entity.name.function.prototype.systemverilog
//                                   ^^^^^^^^ storage.type.systemverilog
            import function logic parity_gen(packet_t data)
//          ^^^^^^ keyword.other.systemverilog
//                 ^^^^^^^^ keyword.other.systemverilog
//                          ^^^^^^ storage.type.systemverilog
//                                ^^^^^^^^^^ entity.name.function.systemverilog
//                                           ^^^^^^^^ storage.type.systemverilog
        );

    endinterface

  interface class ihello;

    pure virtual function void hello();
    pure virtual function void world();
  endclass : ihello

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

typedef interface class ftd_c_t;
//      ^^^^^^^^^^^^^^^ keyword.other.systemverilog
//                      ^^^^^^^ meta.typedef_forward.systemverilog storage.type.userdefined.systemverilog
typedef class  ftd_c_t;
//      ^^^^^ keyword.other.systemverilog
//             ^^^^^^^ meta.typedef_forward.systemverilog storage.type.userdefined.systemverilog
typedef struct ftd_s_t;
//      ^^^^^^ keyword.other.systemverilog
//             ^^^^^^^ meta.typedef_forward.systemverilog storage.type.userdefined.systemverilog
typedef union  ftd_u_t;
//      ^^^^^ keyword.other.systemverilog
//             ^^^^^^^ meta.typedef_forward.systemverilog storage.type.userdefined.systemverilog
typedef enum   ftd_e_t;
//      ^^^^ keyword.other.systemverilog
//             ^^^^^^^ meta.typedef_forward.systemverilog storage.type.userdefined.systemverilog
typedef ftd_t;
//      ^^^^^ meta.typedef_symbol storage.type.systemverilog

typedef enum logic [4:0] {
    ISA_ADD = {OP_RR, RR_ADD},
    ISA_SUB = {OP_RR, RR_SUB},
//  ^^^^^^^ meta.typedef_symbol constant.other.net.systemverilog
    ISA_BEQ = {OP_BR, 3'bXXX}
}  isa_t;
// ^^^^^ meta.typedef_symbol entity.name.type.systemverilog

typedef enum {M[2], N, O, P} b__t;
//              ^ meta.typedef_symbol constant.numeric.decimal.systemverilog
//                           ^^^^ meta.typedef_symbol entity.name.type.systemverilog

  typedef enum logic {TRUE=0, FASLE=0} z_t;
//                        ^ meta.typedef_symbol keyword.operator.assignment.systemverilog
//                                     ^^^ meta.typedef_symbol entity.name.type.systemverilog
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
//        ^^^^^^^^^^^ meta.module.inst.systemverilog entity.name.type.module.systemverilog
  (
    .if1(if1),
    .if2,
//  ^ meta.module.inst.systemverilog punctuation.accessor.dot.systemverilog
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


bind bind_assertion   assertion_ip      i_assert_ip (
// <- keyword.control.systemverilog
//                    ^^^^^^^^^^^^ storage.type.module.systemverilog
//                                      ^^^^^^^^^^^ entity.name.type.module.systemverilog
   .clk_ip   (clk),
//  ^^^^^^ support.function.port.systemverilog
//            ^^^^^^ meta.module.inst.systemverilog
 .req_ip   (req),
 .reset_ip (reset),
 .gnt_ip   (gnt)
);

bind i_dut dut_tb_bind#(
// <- meta.module.inst.systemverilog keyword.control.systemverilog
//         ^^^^^^^^^^^ storage.type.module.systemverilog
    .DATA_W   (DATA_W   ),
//   ^^^^^^ meta.bind.param.systemverilog support.function.port.systemverilog
    .MODE(1'b1),
    .STRING("config")
 ) i_bind(.*);
// ^^^^^^ meta.module.inst.systemverilog entity.name.type.module.systemverilog

/*------------------------------------------------------------------------------
--  Structure / Typedef
------------------------------------------------------------------------------*/
typedef struct {logic a; int b; bit [3:0] c;} mystruct;
//             ^ keyword.operator.other.systemverilog
//                                          ^ meta.typedef_symbol meta.struct.anonymous.systemverilog keyword.operator.other.systemverilog
protected const mystruct c_var = '{a:0, b:1, c:4'hD, default:0, e: mytype'(50)};
//                                 ^ support.function.field
//                                                   ^^^^^^^ meta.struct.assign keyword.control

/*------------------------------------------------------------------------------
--  Class
------------------------------------------------------------------------------*/

class Foo implements Bar, Blah; extends Bar;
//    ^^^ entity.name.type.class.systemverilog
//        ^^^^^^^^^^ keyword.control.systemverilog
//                   ^^^ entity.other.inherited-class.systemverilog
//                        ^^^^ entity.other.inherited-class.systemverilog
//                              ^^^^^^^ keyword.control.systemverilog
//                                      ^^^ entity.other.inherited-class.systemverilog
endclass
// <- keyword.control.systemverilog

interface class base_ic;
// <- keyword.control.systemverilog
//        ^^^^^ keyword.control.systemverilog
//              ^^^^^^^ entity.name.type.class.systemverilog
  pure virtual task pure_task1;
//             ^^^^ keyword.control.systemverilog
//                  ^^^^^^^^^^ entity.name.function.systemverilog
  pure virtual task pure_task2(arg_type arg);
//             ^^^^ keyword.control.systemverilog
//                  ^^^^^^^^^^ entity.name.function.systemverilog
//                             ^^^^^^^^ meta.task.port.systemverilog storage.type.systemverilog

endclass

/*------------------------------------------------------------------------------
--  Task & functions
------------------------------------------------------------------------------*/

task connect(virtual nfc_ip_top_if dut_if);
// <- keyword.control
//   ^ entity.name.function
//           ^ keyword.other
//                   ^ storage.type
endtask : connec
//        ^ meta.task.body.systemverilog invalid.illegal.systemverilog

function void my_pkg::my_func(ref logic d, input int din,
//            ^ support.type.scope.systemverilog
//                  ^ keyword.operator.scope.systemverilog
                      input bit[3:0] d,
                      output bit[$clog(kk)-1:0] d2,
//                               ^ support.function.system.systemverilog
                      output dout);
    $display("d=%0d",d);
    if(d==0)
        d = 1;
    else if(din!=0)
        d = 0
    cfg = '{
       f1      : 1,
//     ^^ support.function.field.systemverilog
       f2      : active,
       default : 0
//     ^^^^^^^ keyword.control.systemverilog
    };
    case (state)
        S_IDLE:// comment
//                ^^^^^^^^ comment
            d = 1;
        default : /* default */ d=0;
    endcase
    return null;
//  ^^^^^^ keyword.control.systemverilog
//         ^^^^ support.constant.systemverilog
endfunction : my_func

        function automatic integer CLOGB2;
//      ^^^^^^^^ meta.function.systemverilog keyword.control.systemverilog
//                         ^^^^^^^ storage.type.systemverilog
//                                 ^^^^^^ entity.name.function.systemverilog
        endfunction : CLOG
//                    ^^^^ invalid.illegal.systemverilog

   import "DPI-C" function void rnd(input int a, output int unsigned b);
// ^^^^^^ keyword.control.systemverilog
//         ^^^^^ string.quoted.double.systemverilog
//                ^^^^^^^^ keyword.control.systemverilog
  export "DPI-C" function dpi_report_error;
//^^^^^^ meta.function.prototype.systemverilog keyword.control.systemverilog
//               ^^^^^^^^ meta.function.prototype.systemverilog keyword.control.systemverilog
//                        ^^^^^^^^^^^^^^^^ meta.function.prototype.systemverilog entity.name.function.systemverilog
import "DPI-C" pure function real cos  (input real a);
//             ^^^^ meta.function.prototype.systemverilog keyword.control.systemverilog
//                                ^^^ meta.function.prototype.systemverilog entity.name.function.systemverilog

function automatic logic [$clog2(4)-1:0] first_func (logic in, int unsigned a);
//                        ^^^^^^ support.function.system.systemverilog
//                                       ^^^^^^^^^^ meta.function.systemverilog meta.function.body.systemverilog entity.name.function.systemverilog
//                                                                 ^^^^^^^^ storage.type
  return '0;
endfunction : first_func
//            ^^^^^^^^^^ entity.label.systemverilog

function automatic test_t [1:0] my_func (test_t in);
//                 ^^^^^^ meta.function.systemverilog storage.type.userdefined.systemverilog
   my_func = in;

endfunction

function automatic test_t my_func (test_t in);
//                 ^^^^^^ meta.function.systemverilog storage.type.userdefined.systemverilog
   my_func = in;

endfunction

task first_task (int unsigned a);
// <- meta.task.systemverilog keyword.control.systemverilog
//   ^^^^^^^^^^ meta.task.systemverilog entity.name.function.systemverilog
//               ^^^ meta.task.port.systemverilog storage.type.systemverilog
//                   ^^^^^^^^ meta.task.body.systemverilog meta.task.port.systemverilog storage.type.systemverilog
  #1step;
//^ meta.task.body.systemverilog keyword.operator.delay.systemverilog
// ^^^^^ keyword.other.systemverilog
endtask : first_task

function test_t [1:0] my_func (test_t in);
//       ^^^^^^ meta.function.systemverilog storage.type.userdefined.systemverilog
   my_func = in;
endfunction : my_func

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

extern constraint proto1;
//                ^^^^^^ entity.name.section.systemverilog

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
//                 ^ meta.block.constraint.systemverilog punctuation.section.block.constraint.begin.systemverilog
//                          ^^^^^^ keyword.other.systemverilog
//                                                                         ^ punctuation.section.block.constraint.end.systemverilog

assert(a.randomize(ack) with {}; );
// <- keyword.control.systemverilog
//       ^^^^^^^^^ support.function.generic.systemverilog
/*------------------------------------------------------------------------------
--  MISC
------------------------------------------------------------------------------*/

  $sformatf("%s %h %b %c %d %l %m %o %p %x %u %t %v %z %e %f %g %%1 ");
  $sformatf("%S %H %B %C %D %L %M %O %P %X %U %T %V %Z %E %F %G");

  $sformatf("%0d %1h %2s", 4'b01xz);
  $sformatf("%4.3f %3e %-5.4g", a,b,c);

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
    disable fork;
//  ^^^^^^^ keyword.control.systemverilog
join : f_label


always_ff @(posedge clk or negedge rst_n) begin : proc_
    if (~rst_n)
        a <= '0;
else if (en)
// <- keyword.control.systemverilog
        a <= int'(a) + b;
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


`ifdef SIGNED_FEATURES
//     ^^^^^^^^^^^^^^^ support.variable.systemverilog
    typedef logic signed [3:0] mytype;
`elsif UNSIGNED_FEATURES
//     ^^^^^^^^^^^^^^^^^ support.variable.systemverilog
    typedef logic unsigned [3:0] mytype;
`endif

/*------------------------------------------------------------------------------
--  Rand sequence
------------------------------------------------------------------------------*/

task randseq1;

  randsequence(m)
    m : {x=1;};

    PP_OP : if ( depth < 2 ) PUSH_OPER else POP ;
    PUSH_OPER : repeat( $urandom_range( 2, 6 ) ) PUSH ;
    PUSH : { ++depth; do_push(); };
    POP : { --depth; do_pop(); };

    TOP : rand join (0.0) SETUP P2 ;
    SETUP : { if( fifo_length >= max_length ) break; } COMMAND ;
    P2 : A { if( flag == 1 ) return; } B C ;
    A : { $display( "A" ); } ;
    B : { if( flag == 2 ) return; $display( "B" ); } ;

    SELECT : case ( device & 7 )
      0 : NETWORK ;
      1, 2 : DISK ;
      default : MEMORY ;
    endcase ;

    main : first second gen ;
    first :  add := 3
          | dec := (1 + 1) // 2
          ;
    second : pop | push ;
    add : gen("add") ;
    dec : gen("dec") ;
    pop : gen("pop") ;
    push : gen("push") ;
    gen ( string s = "done" ) : { $display( s ); } ;

  endsequence

endtask : randseq1

task mytask();
   repeat(5) randsequence(main)
      main:{};
//    ^^^^ meta.randsequence.systemverilog entity.name.tag.systemverilog
   endsequence
endtask:mytask

function void randseq2();

  randsequence(m)
    void A : A1 A2;
    void A1 : { cnt = 1; } B repeat(5) C B
      { $display("c=%d, b1=%d, b2=%d", C, B[1], B[2]); }
    ;
    void A2 : if (cond) D(5) else D(20)
      { $display("d1=%d, d2=%d", D[1], D[2]); }
    ;
    int B : C { return C;}
      | C C { return C[2]; }
      | C C C { return C[3]; }
      ;
    int C : { cnt = cnt + 1; return cnt; };
    int D (int prm) : { return prm; };
  endsequence

endfunction : randseq2 ;

/*------------------------------------------------------------------------------
--  Extern
------------------------------------------------------------------------------*/
extern protected static function bit check_data_width(int unsigned width);

extern module a #(parameter size= 8, parameter type TP = logic [7:0])
 (input [size:0] a, output TP b);

   extern virtual function bit Xcheck_accessX
// ^^^^^^ meta.declaration.extern.systemverilog keyword.control.systemverilog
//        ^^^^^^^ meta.declaration.extern.systemverilog keyword.control.systemverilog
//                ^^^^^^^^ meta.function.prototype.systemverilog keyword.control.systemverilog
//                         ^^^ meta.function.prototype.systemverilog storage.type.systemverilog
                                (input uvm_reg_item rw,
                                 output uvm_reg_map_info map_info,
                                 input string caller);


    extern virtual task do_write(uvm_reg_item rw);
//  ^^^^^^ meta.declaration.extern.systemverilog keyword.control.systemverilog
//         ^^^^^^^ keyword.control.systemverilog
//                 ^^^^ keyword.control.systemverilog
//                      ^^^^^^^^ entity.name.function.systemverilog
//                               ^^^^^^^^^^^^ meta.task.port.systemverilog storage.type.systemverilog
