interface my_interface1;
    logic   one;
    logic   two;

    modport sys (
        output one,
        output two
    );

endinterface

interface my_interface2;
    logic   one;
    logic   two;

    modport sys (
        output one,
        output two
    );

endinterface


module my_module
(
    my_interface1                       if1,
    my_interface2                       if2,
    input   logic                       clk,
    output  wire                        my_out

);

parameter
    my_module.test_param = 23;


