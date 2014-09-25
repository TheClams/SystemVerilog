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
    logic [15:0] P2 = 0,
    real P3 = my_pkg::pp,
    )
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
t_byte b2 = 8'hFF;

logic [3:0]  sig_logic = 4'shC;

// psl a_mypsl_assert: assert never {sig_logic!=4'hX};

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

function void my_func(ref logic d, input int din, output dout);
    $display("d=%0d",d);
endfunction : my_func

fork
join_any

fork : f_label
    begin : b_label

    end : b_label
join : f_label