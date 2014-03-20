`define my_macro ;
`my_macro

interface my_interface1;
    logic   one;
    logic   two;

    modport sys (
        input one,
        output two
    );

endinterface

    interface my_interface2;
        logic   one;
        logic   two;

        modport sys (
            inout one,
            output two
        );

    endinterface


module my_module
  #(parameter int P1=0)
  (
    my_interface1.sys   if1,
    my_interface2       if2,
    input   logic       clk,
    output  wire        my_out
  );

    timeunit 1ns;
timeprecision 1fs;

    typedef my_module#(16)  t_my_module_16;
    typedef logic[7:0]  t_byte;
    t_byte  b0, // Comments
            b1;

logic [3:0]  sig_logic;

my_interface1 if1();

my_module i_my_module
  (
    .if1(if1),
    .if2(if2),
    .clk(clk),
    .my_out(my_out),
  );

parameter
    my_module.test_param = 23;

    typedef my_module#(16)  t_my_module_16;

function void my_func(ref logic d, input int din, output dout);
