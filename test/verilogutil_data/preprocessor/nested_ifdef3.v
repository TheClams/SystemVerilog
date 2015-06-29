`ifdef first_block
    `ifndef second_nest
        first_block is defined
    `else
        first_block and second_nest defined
    `endif
    `elsif second_block
        second_block defined, first_block is not
    `else
        `ifndef last_result
            first_block, second_block, last_result not defined
        `elsif real_last
            first_block, second_block not defined, last_result and real_last defined
        `else
            Only last_result defined
    `endif
`endif

