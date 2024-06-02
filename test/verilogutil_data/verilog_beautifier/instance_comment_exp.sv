sub_mod1 #(.PARA1(PARA1)) inst1 ( //this comment will lead to error
    .io1(sm1),
    .io2(sm2),
    .io3(sm3)
);

sub_mod1 #(.PARA2(PARA2)) inst2 (
    // IOs
    .io1(sm1),
    .io2(sm2),
    .io3(sm3)
    //this comment will lead to error
);