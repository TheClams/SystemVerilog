module dcs_packet_rx_v2 #(
    parameter  int  unsigned pDataWidth = 20           ,
    parameter                pBaud      = 115_200      ,
    parameter  time          t          = 1.5e-3       ,
    localparam int           lpBaud     = $clog2(pBaud)
) (
    input iClk
);
endmodule