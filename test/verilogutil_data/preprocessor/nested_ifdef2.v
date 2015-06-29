`define wow
`define nest_one
`define second_nest
`define nest_two

`ifdef wow
    wow is defined
    `ifdef nest_one
        nest_one is defined
        `ifdef nest_two
            nest_two is defined
        `else
            nest_two is not defined
        `endif
    `else
        nest_one is not defined
    `endif
`else
    wow is not defined
    `ifdef second_nest
        nest_two is defined
    `else
        nest_two is not defined
    `endif
`endif