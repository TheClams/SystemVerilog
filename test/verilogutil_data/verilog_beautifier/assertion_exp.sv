module assertions_test #(parameter SIZE = pa_test::SIZE) (
    in_Apb.mo_monitor_slave uin_ApbBus  ,
    in_Apb.mo_monitor_slave uin_ApbSlave,
    input logic             test        ,
    input logic             ckTest
);
    int errorCnt;

    property p_test(N);
        @(posedge ckTest)
            uin_ApbBus.apbPSel[N] |-> test;
    endproperty

    sequence s_read(N);
        @(posedge ckTest)
            !uin_ApbBus.apbPWrite[N] && uin_ApbBus.apbPSel[N] && !uin_ApbBus.apbPEnable[N] ##1
            !uin_ApbBus.apbPWrite[N] && uin_ApbBus.apbPSel[N] && uin_ApbBus.apbPEnable[N] ##[1:$]
            !uin_ApbBus.apbPEnable[N];
    endsequence

    assert property (p_test(0))
        else begin $error("Assertion checkConnection failed."); errorCnt=errorCnt+1; end

    cover sequence (s_read(N)) ;

endmodule