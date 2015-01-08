module crc0x31(
    input logic [7:0] iData,
    input logic [7:0] iCrcPrev,
    output logic [7:0] oCrcNew
);


assign oCrcNew[0] = iData[0] ^ iCrcPrev[0];

endmodule