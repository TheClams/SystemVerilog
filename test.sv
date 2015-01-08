`define my_macro ;
`my_macro

interface my_interface1;
    logic   one;
    logic   two;

    modport sys (
        input one,
        output two
    );
endinterface // my_interface1

typedef logic [31:0] queue_of_levels [$];


    interface my_interface2;
        logic   one;
        logic   two;

        modport sys (
            inout one,
            output two
        );

    endinterface

module my_module
  #(parameter int P1=0,
    logic [15:0] P2 = 16'b0000_1111,
    real P3 = my_pkg::pp,
    )
  (
    my_interface1.sys   if1,
    my_interface2       if2, // Coment if2
    input   logic       clk, /* comment clk */
    output  wire        my_out
  );

    timeunit 1ns;
timeprecision 1fs;

    typedef my_module#(16)  t_my_module_16;
    typedef logic[7:0]  t_byte;
    t_byte  b0, // Comments
            b1;
local t_byte b2 = 8'hFF;

logic [3:0]  sig_logic = 4'shC;

// psl a_mypsl_assert: assert never {sig_logic!=4'hX};

my_interface1#(1) if1(clk,rst_n);
    virtual my_interface1#(3,4) if2;

my_module i_my_module
  (
    .if1(if1),
    .if2(if2),
    .clk(clk),
    .my_out(my_out),
  );

parameter
    my_module.test_param = 23'h44;

localparam mytype myvar = mytype'(MY_INIT/4+8);
localparam myvar1 = MY_INIT1;
localparam logic [1:0] myvar2 = MY_INIT2;
protected const mystruct c_var = '{a:0,b:1,c:4'hD};

function void my_func(ref logic d, input int din,
                      input bit[3:0] d,
                      output dout);
    $display("d=%0d",d);
endfunction : my_func

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