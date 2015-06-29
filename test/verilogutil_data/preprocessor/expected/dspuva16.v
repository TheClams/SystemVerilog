module DSPuva16 (CLK, RESET,  PC, IR,  DIN, DOUT, DOUT24, PORT, IOR, IOW,PING) ;
	parameter			Model = 0;
	input  				CLK;
	input  				RESET;
	input 				PING;
	output [Model+7:0]	PC;
	input       [15:0]	IR;
	input       [23:0]	DIN;
	output      [15:0]	DOUT;
	output 		[23:0]  DOUT24;
	output       [7:0]	PORT;
	output				IOR, IOW;
	reg         [11:0]	NextPC;
	reg         [15:0]	RegIR;
	reg         [23:0]	ACC;
	wire        [23:0]	DataBus;
	wire        [23:0]	RegOut;
	reg	       			Flag;
	reg [1:0] State;
	parameter [1:0] st0 = 2'b00, st1 = 2'b01, st2 = 2'b11, st3 = 2'b10;
	always @(posedge CLK or posedge RESET)
	begin
		if (RESET)	State	<= st0;
		else if (PING) State <= st0;
		else case (State)
			st0:	State	<= st1;
			st1:	State	<= st2;
			st2:	State	<= st3;
			st3:	State	<= st0;
		endcase
	end
	wire [3:0]			OpCode	= RegIR[15:12];
	wire [3:0]			rD		= RegIR[11: 8];
	wire [3:0]			rS		= RegIR[ 7: 4];
	wire [3:0]			rT		= RegIR[ 3: 0];
	wire [7:0]			RelAddr	= RegIR[ 7: 0];
	wire [7:0]			AbsAddr	= RegIR[11: 4];
	wire [7:0]			IOaddr	= RegIR[ 7: 0];
	reg			OldMAC;
	reg  [3:0]	OldRegD;
	reg  [3:0]	FlagSelect;
	always @(posedge CLK or posedge RESET)
	begin
		if      (RESET)		OldMAC <= 0;
		else if ((State == st1))	OldMAC <= (OpCode[3:2] == 2'b01);
		if      (RESET)		OldRegD <= 0;
		else if ((State == st1))	OldRegD <= rD;
		if      (RESET)		FlagSelect <= 0;
		else if ((State == st1))	FlagSelect <= IR[11:8];
		if      (RESET)									RegIR <= 0;
		else if ((State == st1))								RegIR <= IR;
		else if (((State == st2) | (State == st3)) & ((OpCode[3:2] == 2'b10) & ~RegIR[13]))	RegIR <= {OpCode, rS, rS, rT};
	end
	reg	PCinc, PCflag;
	wire [12:0]	PCmask  = (PCflag) ? {RelAddr[7],RelAddr[7],RelAddr[7],RelAddr[7], RelAddr[7:0], 1'b1} : 13'h0001;
	wire [12:0]	PCadder = {NextPC, PCinc} + PCmask;
	always @(posedge CLK or posedge RESET)
	begin
		if (RESET)
		begin
			NextPC <= 0;
			PCinc  <= 0;
			PCflag <= 0;
		end
		else if(PING)
		begin
			NextPC <= 1;
			PCinc  <= 0;
			PCflag <= 0;
		end
		else
		begin
			if      ((State == st3) & (OpCode == 4'b0000))	NextPC <= (AbsAddr << Model);
			else if ((State == st3) & ((OpCode == 4'b0001) & ~RegIR[11]))		NextPC <= RegOut [19:8];
			else							NextPC <= PCadder[12:1];
			PCinc	<= ((State == st0)) | ((State == st2) & (rT == 0) & (OpCode[3:2] != 2'b00));
			PCflag  <= (State == st2) & ((OpCode == 4'b0001) & RegIR[11]) & Flag;
		end
	end
	assign PC = NextPC[Model+7:0];
	reg  [23:0]	RegsBank[0:15];
	reg   [3:0]	RegAddr;
	wire RegWE = ((State == st0) & (OpCode[3]))
			   | ((State == st0) & (OpCode == 4'b0010))
			   | ((State == st1) &  OldMAC)
			   | ((State == st3) & (OpCode == 4'b0000));
   	always @(posedge CLK or posedge RESET)
	begin
		if (RESET)	RegAddr <= 0;
		else case (State)
			st0:	RegAddr <= OldRegD;
			st1:	RegAddr <= IR[7:4];
			st2:	RegAddr <= rT;
			st3:	RegAddr <= rD;
		endcase
	end
	always @(posedge CLK)
	begin
		if (RegWE)
			RegsBank[RegAddr] <= DataBus;
	end
	assign RegOut = RegsBank[RegAddr];
	always @(posedge CLK or posedge RESET)
	begin
		if (RESET)	ACC <= 0;
		else 		ACC <= RegOut;
	end
	wire [23:0]	ALUmac, ALUlogic, ALUarith;
	wire [23:0]	RegS = (rS == 0) ? 24'h000000  : ACC;
	wire [23:0]	RegT = (rT == 0) ? {IR, 8'h00} : RegOut;
	reg  [23:0]	OpA, OpB;
	always @(posedge CLK)
	begin
		OpA <= (State == st3) ? RegS : {OpA[3:0],OpA[23:4]};
		OpB <= (State == st3) ? RegT : OpB;
	end
	assign ALUlogic = OpCode[1:0] == 2'b00 ?   OpA & OpB
	                : OpCode[1:0] == 2'b01  ?   OpA | OpB
	                : OpCode[1:0] == 2'b10 ? ~(OpA | OpB)
	                :                            OpA ^ OpB;
	wire		aluCarry;
	wire [23:0] AddA = ((OpCode[1] | ~Flag) ? OpA : 24'h000000);
	wire [23:0] AddB = ((OpCode[1] |  Flag) ? OpB : 24'h000000);
	assign {aluCarry, ALUarith} = OpCode[0] ? (AddA - AddB) : (AddA + AddB);
	wire ALUoverflow = (aluCarry ^ ALUarith[23] ^ AddA[23] ^ AddB[23]);
	wire    [3:0]	InA = OpA[11:8];
	wire   [15:0]	InB = OpB[23:8];
	wire   [17:0]	Op1 = (InA[0] ? {InB[15], InB[15], InB} : 18'h00000);
	wire   [17:0]	Op2 = (InA[1] ? {InB[15], InB, 1'b0   } : 18'h00000);
	wire   [17:0]	Op3 = Op1 + Op2;
	wire   [18:0]	Op4 = (InA[2] ? {InB[15], InB[15], InB, 1'b1} : 19'h00001);
	wire   [18:0]	Op5 = (State == st3)
					    ? (InA[3] ? {~InB[15], ~InB, 2'b11} : 19'h00000)
					    : (InA[3] ? { InB[15],  InB, 2'b00} : 19'h00000);
	wire   [18:0]	Op6 = Op4 + Op5;
	reg    [19:0]	Op7;
	reg    [31:0]	AxB;
	reg     [1:0]	OldCode;
	wire   [31:0]	Op8 = (State == st1) ? 32'h00000000
					    : {AxB[31], AxB[31], AxB[31], AxB[31], AxB[31:4]};
	always @(posedge CLK)
	begin
		Op7 <= {Op3[17], Op3[17], Op3} + {Op6[18:1], 2'b00};
		AxB <= Op8 + {Op7, 12'h000};
		OldCode <= (State == st1) ? OpCode[1:0] : OldCode;
	end
	wire x;
	wire [23:0] AccA = (OldCode[1]) ? RegOut : 24'h000000;
	wire [23:0] AccB = (OldCode[1:0] == 2'b01) ? AxB[23:0]
					 : (~OldCode[0])           ? AxB[30:7]
					 :                          ~AxB[30:7];
	assign {ALUmac,x} = {AccA, 1'b1} + {AccB, OldCode[0]};
	assign  DataBus = ((State == st0) & (OpCode[3:2] == 2'b10))	? ALUarith	   : 24'bz;
	assign  DataBus = ((State == st0) & (OpCode[3:2] == 2'b11))	? ALUlogic	   : 24'bz;
	assign  DataBus = ((State == st1))				? ALUmac	   : 24'bz;
	assign  DataBus = ((State == st3) | (State == st2))	? { PC, 8'h00} : 24'bz;
	assign  DataBus = ((State == st0) & (OpCode[3:2] == 2'b00))	? {DIN}        : 24'bz;
	assign  DataBus = ((State == st0) & (OpCode[3:2] == 2'b01))	? 24'hFFFFFF   : 24'bz;
	reg	ZFF, SFF, VFF;
	always @(posedge CLK or posedge RESET)
	begin
		if (RESET)
			{ZFF, SFF, VFF} <= 0;
		else if ((State == st0))
		begin
			ZFF <= (DataBus == 0);
			SFF <= DataBus[23];
			VFF <= ALUoverflow;
		end
	end
	always @(ZFF or SFF or VFF or FlagSelect)
	begin
		case (FlagSelect[2:0])
			3'b000:	Flag =  ZFF;
			3'b001:	Flag = ~ZFF;
			3'b010:	Flag =  VFF;
			3'b011:	Flag = ~VFF;
			3'b100:	Flag =  SFF & ~ZFF;
			3'b101:	Flag =  SFF |  ZFF;
			3'b110:	Flag = ~SFF & ~ZFF;
			3'b111:	Flag = ~SFF |  ZFF;
		endcase
	end
	reg  [7:0]	PORT;
	reg			IOR, IOW;
	always @(posedge CLK or posedge RESET)
	begin
		if (RESET)
			PORT <= 0;
		else if ((State == st2))
		begin

				PORT <= IOaddr;
		end
		if (RESET)	IOW <= 0;
		else		IOW <= (State == st3) & (OpCode == 4'b0011);
		if (RESET)	IOR <= 0;
		else		IOR <= (State == st3) & (OpCode == 4'b0010);
	end
	assign	DOUT = RegOut[23:8];
	assign  DOUT24 = RegOut;
endmodule