function void f();
    int x=0;
    `uvm_fatal("x","y")
    x++;

    if (1)
        `uvm_info("", "", UVM_LOW)
    else
        `uvm_info("", "", UVM_LOW)

    `uvm_info("", "", UVM_LOW)

    if (0)
        `uvm_info("", "", UVM_LOW)
    else
        `uvm_info("", "", UVM_LOW)

endfunction