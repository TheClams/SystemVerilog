//
// PROJECT:	OpenDSP - The 'DSPuva16' 16-bit fixed-point DSP for FPGA
//			http://www.DTE.eis.uva.es/OpenProjects/OpenDSP/index.htm
//
// RIGHTS:	Santiago de Pablo
//			Copyright (c) 2001-2004. All Rights Reserved.
//
// GPL:		You may freely copy, change, and distribute it,
//			but you may not impose restrictions on further distribution,
//			and you must make the source code available.
//
//			This code is supplied "as is", without any warranty.
//			Please, tell us how many devices you have implemented.
//
// AUTHOR:	Santiago de Pablo      (sanpab@eis.uva.es)
//			Department of Electronics Technology (DTE)
//			University of Valladolid           (Spain)
//
// MODULE:	DSPuva16.v
//
// DESCRIPTION:
//			The 'DSPuva16' is a 16-bit fixed-point DSP processor for FPGA.
//			It has 16 internal 24-bit registers, r0 to r15, but it has no more memory.
//			All registers, except r0, can be used in all operations.
//			It operates with three operands, registers or constants (rD = rS|0 op rT|K).
//			It can execute 16x16 MAC operations (rD = rD +/- rS * rT) in one instruction cycle.
//			The ALU has eight 24-bit operations: logic, arithmetic and conditional assignment.
//			Precission is extended up to 24 bits (from <1.15> to <1.23>) in all operations.
//			The executable code is from 256 words (version 'A') up to 4K words (version 'E').
//			External accesses are made synchronously through 256 direct I/O ports (p0 to p255).
//
//			Multiplies in four stages two 16-bit values using fixed point.
//			The 16-bit inputs must be valid during the forth subcycle (st3).
//			One cycle (four subcycles) latency is introduced for product operations.
//			The 32-bit output is valid only during the second subcycle (st1).
//			It can multiply two new values each instruction cycle (every 100ns at 40 MHz).
//
//			The size of the processor core is about 250 slices (500 LCs) in Virtex/Spartan2 FPGAs.
//			Up to sixteen 16-words memory blocks can be added, with only 17 LCs for each one.
//			All components can be integrated in the same FPGA: core, code memory, ports and added memory.
//
// VERSIONS:
//			'A' has 256x16 code; 'B' has 512x16; 'C' has 1Kx16; 'D' has 2Kx16; 'E' has 4Kx16.
//
// REVISION:
//			2.02	2004-07-10	Changing I/O instructions opcodes
//			2.00	2004-07-10	***New opcode with 256 ports***
//			1.10	2004-05-25	Changes on MAC while implementation (it works fine at 40 MHz)
//			1.08	2004-04-15	Changes on ALU while implementation
//			1.06	2004-04-02	Changing rS and rT reading order
//			1.04	2004-04-01	All in one file (same behaviour)
//			1.02	2001-04-21	Introducing ACC
//			1.00	2001-04-16	First stable version (HDL simulation only)
//			0.25	2001-04-11	Adding MODELs for 256-4K code.
//			0.23	2001-04-09	Checking for '<='
//			0.21	2001-03-26	First public version (not simulated yet)
//			0.19	2001-03-18	More code
//			0.17	2001-02-09	More code
//			0.15	2000-12-21	Successful compilation in Verilog
//			0.13	2000-12-19	Initial version in Verilog
//			0.11	2000-12-09	Initial version in VHDL
//
// TO DO LIST:
//			Beta tests.
//			Better Test Bench.
//			Test with Program Memory (done).
//			Generate V flag with MAC?
//			16-bit ports or 24-bit ports?
//
// OPCODES:	nop            rD =      rS x rT   ifFlag R = T      rD = rS and rT   rD = 0
//			break          rD =      rS x K    ifFlag R = K      rD = rS and K    rD = K
//			ret (rS)       rD =      rS * rT   ifFlag R = -T     rD = rS or  rT   rD = -K
//			rD = pN 	   rD =      rS * K    ifFlag R = -K     rD = rS or  K    rD = rT
//			pN = rD	       rD = rD + rS * rT   rD = rS + rT      rD = rS nor rT   rD = -rT
//			jpFlag nn      rD = rD + rS * K    rD = rS + K       rD = rS nor K    rD = not rT
//			goto nn        rD = rD - rS * rT   rD = rS - rT      rD = rS xor rT   rD = not K
//			call (rD) nn   rD = rD - rS * K    rD = rS - K       rD = rS xor K    -
//
//
//	Opcodes and macros:
//  ------------------------------------------------
//			0000 AAAA AAAA DDDD  call (rD) Addr		Absolute jump (rD = PC + 1; PC = Addr << Model)
//			0001 0XXX XXXX SSSS  ret (rS)			Use 'rS' to return from a subroutine (PC = rS)
//			0001 1FFF AAAA AAAA  jpFlag RelAddr		Relative jump in +/-128 instructions
//			0010 DDDD NNNN NNNN  rD = pN			Read from a direct port, from p0 to p255
//			0011 SSSS NNNN NNNN  pN = rS			Write through a direct port, from p0 to p255
//
//			0100 DDDD SSSS TTTT  rD  = rS * rT		Normalized product: <1.15> * <1.15> => <1.23>
//			0101 DDDD SSSS TTTT  rD  = rS x rT		Shifter product:    <1.15> x <8.8>  => <1.23>
//			0110 DDDD SSSS TTTT  rD += rS * rT		MAC with positive accumulation
//			0111 DDDD SSSS TTTT  rD -= rS * rT		MAC with negative accumulation
//
//			1000 DDDD SSSS TTTT  ifFlag rD =  rT	Conditional assignment
//			1001 DDDD SSSS TTTT  ifFlag rD = -rT	Conditional assignment with sign exchange
//			1010 DDDD SSSS TTTT  rD = rS + rT		Addition and more: rD = rT; rD = K; rD = rS + K.
//			1011 DDDD SSSS TTTT  rD = rS - rT		Substraction and more: rD = -rT.
//
//			1100 DDDD SSSS TTTT  rD = rS and rT		break => r1 = r1 and r1
//			1101 DDDD SSSS TTTT  rD = rS or  rT		nop	  => r1 = r1 or  r1
//			1110 DDDD SSSS TTTT  rD = rS nor rT		not   => rD =  0 nor rT
//			1111 DDDD SSSS TTTT  rD = rS xor rT
//
//
// FLAGS:	(eq), (ne), (v), (nv), (ge), (gt), (le), (lt).
//
// MAC SIMULATION:
//			0x53A2 (+0'6534) * 0x6B1f (+0'8369) = 0x22FED69E => 0x45FDAD (+0'5468) ok
// 			0xDB1f (-0'2881) * 0x53A2 (+0'6534) = 0xF3F3B69E => 0xE7E76D (-0,1882) ok
// 			0x53A2 (+0'6534) * 0xDB1f (-0'2881) = 0xF3F3B69E => 0xE7E76D (-0,1882) ok
// 			0xDB1f (-0'2881) * 0xB3A2 (-0,5966) = 0x0B00569E => 0x1600AD (+0,1719) ok
//
// BUGS:	Please, report bugs to "sanpab@eis.uva.es" with reference "OpenDSP v2.00".
//


// Additions
// 1. Add PING Input - analog IRQ
// 2. Add two bits to DIN
`define	LOW_LOGIC		// Valid LOW_POWER or LOW_LOGIC


//
// DSPuva16 Core
//

module DSPuva16 (CLK, RESET,  PC, IR,  DIN, DOUT, DOUT24, PORT, IOR, IOW,PING)/* synthesis syn_preserve = 1*/;

	parameter			Model = 0;	// Model 'A' uses 0, 'B' uses 1, ..., 'E' uses 4.

	input  				CLK;		// 40 MHz Clock (=> 100ns/instruction)
	input  				RESET;		// Active-high external Reset
	input 				PING;			// Goto 0

	output [Model+7:0]	PC;			// Program Memory Address
	input       [15:0]	IR;			// Program Memory Data (always read)

	input       [23:0]	DIN;		// Input Data Port
	output      [15:0]	DOUT;		// Output Data Port
	output 		[23:0]  DOUT24;		// Output Data Port 24 bit width
	output       [7:0]	PORT;		// Port Address
	output				IOR, IOW;	// Port Read and Write signals, active high


	// Internal Registers and Buses:

	reg         [11:0]	NextPC;		// Program Counter (up to 4K code)
	reg         [15:0]	RegIR;		// Instruction Register
	reg         [23:0]	ACC;		// Accumulator for 'rT'
	wire        [23:0]	DataBus;	// Internal Data Bus
	wire        [23:0]	RegOut;		// Output from Register Bank
	reg	       			Flag;		// Selected Flag


//----------------------------------------------------------------------------------------------------------------------//
// State =>	Operations                        Program Counter
//----------------------------------------------------------------------------------------------------------------------//
//  00   =>	Read Instruction                  PC = PC
//	01   =>	RegIR = IR                        PC = PC + 1
//	11   =>	ACC = rS                          PC = PC
//	10   =>	RegT = rT; RegS = ACC             PC = PC/PC+1/PC+nn/nnn
//	00   =>	MAC1 - Writes on rD if ALU        PC = PC
//	01   =>	MAC2                              PC = PC + 1
//	11   =>	MAC3                              PC = PC
//	10   =>	MAC4                              ...
//	00   =>	Last MAC cycle (for segmentation)
//	01   =>	Reads, accumulates and Writes on rD if MAC
//----------------------------------------------------------------------------------------------------------------------\\
//                                                                                                                      //
//       |       Instruction 0 (MAC)      |       Instruction 1 (ALU)      |       Instruction 2 (GOTO)     |           \\
//       | ___     ___     ___     ___    | ___     ___     ___     ___    | ___     ___     ___     ___    | ___     __//
//  CLK	_|/   \___/   \___/   \___/   \___|/   \___/   \___/   \___/   \___|/   \___/   \___/   \___/   \___|/   \___/	\\
//       | _______ _______ _______ _______| _______ _______ _______ _______| _______ _______ _______ _______| _______ __//
//State _|/__st0__/__st1__/__st2__/__st3__|/__st0__/__st1__/__st2__/__st3__|/__st0__/__st1__/__st2__/__st3__|/__st0__/__\\
//      _| _______________ _______________|________________ _______________|________________ _______________| __________//
//   PC _|/_______n_______\______n+1______|_______n+1______\______n+2______|_______n+2______\______n+3______|/__(new)___\\
//      _| _______________ _______________|________________ _______________|________________ _______________|___________//
//RegIR _|/_______x_______\_______I0______|________I0______\_______I1______|________I1______\_______I2______|___________\\
//      _| _______________________________| _______________________________| _______________________________|___________//
//  S,T _|/_______________x_______________|\_____________S0,T0_____________|\_____________S1,T1_____________|\__________\\
//       | _______ _______ _______ _______| _______ _______ _______ _______| _______ _______ _______ _______| _______ __//
//  MAC _|/___x___/___x___/___x___/___x___|/__m0a__/__m0b__/__m0c__/__m0d__|/__m1a__/__m1b__/__m1c__/__m1d__|/__m2a__/__\\
//       |________________________________| _______ _______________________| _______ _______________________| _______ __//
//  ALU _|____x___/___x___/___x___/___x___|/_(OP0)_/___x___/___x___/___x___|/__OP1__/___x___/___x___/___x___|/_(OP2)_/__\\
//       | _______ _______ _______ _______| _______ _______ _______ _______| _______ _______ _______ _______| _______ __//
// Rdir _|/___x___/___x___/___S0__/___T0__|/___R0__/___x___/___S1__/___T1__|/___R1__/___R0__/___S2__/___T2__|/___R2__/__\\
//       |                                |                                | _______ _______                |           //
//  rWE _|________________________________|________________________________|/  ALU1 \  MAC0 \_______________|___________\\
//       |                                |                                | _______                        |           //
//  IOR _|________________________________|________________________________|/ (IN1) \_______________________|___________\\
//       |                                |                                | _______                        |           //
//  IOW _|________________________________|________________________________|/ (OUT1)\_______________________|___________\\
//      _|________________________ _______|________________________ _______|________________________ _______|___________//
// PORT _|________________________\_______|_______AD0______________\_______|_______AD1______________\_______|_______AD2_\\
//                                                                                                                      //
//----------------------------------------------------------------------------------------------------------------------\\


	//
	// Processor Control Unit: State and Decoding
	//

	reg [1:0] State;													// Sequencer
	parameter [1:0] st0 = 2'b00, st1 = 2'b01, st2 = 2'b11, st3 = 2'b10;	// States

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

	`define	PHASE0		(State == st0)
	`define	PHASE1		(State == st1)
	`define	PHASE2		(State == st2)
	`define	PHASE3		(State == st3)

	wire [3:0]			OpCode	= RegIR[15:12];				// Bits used for OpCode
	wire [3:0]			rD		= RegIR[11: 8];				// Bits used for the destination register (rD)
	wire [3:0]			rS		= RegIR[ 7: 4];				// Bits used for the first operand (rS)
	wire [3:0]			rT		= RegIR[ 3: 0];				// Bits used for the second operand (rT)
	wire [7:0]			RelAddr	= RegIR[ 7: 0];				// Bits used for relative addressing
	wire [7:0]			AbsAddr	= RegIR[11: 4];				// Bits used for absolute addressing
	wire [7:0]			IOaddr	= RegIR[ 7: 0];				// Bits used for I/O addressing
//	wire [7:0]			InAddr	= RegIR[ 7: 0];				// Bits used for inport addressing
//	wire [7:0]			OutAddr	= {RegIR[7:4],RegIR[11:8]};	// Bits used for outport addressing

	`define OP_CALL		(OpCode == 4'b0000)					// Absolute jumps for CALL and GOTO
	`define OP_JPRET	(OpCode == 4'b0001)					// Conditional jumps or returns from subroutines
	`define	OP_IN		(OpCode == 4'b0010)					// I/O read operations
	`define	OP_OUT		(OpCode == 4'b0011)					// I/O write operations

	`define	OP_CTRL		(OpCode[3:2] == 2'b00)				// Program Control and I/O operations
	`define	OP_MAC		(OpCode[3:2] == 2'b01)				// MAC operations
	`define	OP_ARITH	(OpCode[3:2] == 2'b10)				// Arithmetic operations
	`define	OP_LOGIC	(OpCode[3:2] == 2'b11)				// Logic operations

	`define OP_ALUMAC	(OpCode[3:2] != 2'b00)				// ALU or MAC operations
	`define	OP_ALU		(OpCode[3])							// Arithmetic or Logic operations
	`define	OP_RET		(`OP_JPRET & ~RegIR[11])			// ret (or iret)
	`define	OP_JP		(`OP_JPRET &  RegIR[11])			// jpFlag
	`define	OP_COND_ASG	(`OP_ARITH & ~RegIR[13])			// ifFlag rD = [-]{rT|K}
	`define	OP_IO		(`OP_IN | `OP_OUT)					// I/O operation
	`define	OUT_IN		(RegIR[12])							// '1' if OUT, '0' if IN



	//
	// Instruction Register: RegIR
	//

	reg			OldMAC;		// Registers 'one' if last instruction was a MAC one
	reg  [3:0]	OldRegD;	// Destination Registry of a MAC instruction
	reg  [3:0]	FlagSelect;	// Flag Selected by the current instruction

	always @(posedge CLK or posedge RESET)
	begin
		if      (RESET)		OldMAC <= 0;
		else if (`PHASE1)	OldMAC <= `OP_MAC;

		if      (RESET)		OldRegD <= 0;
		else if (`PHASE1)	OldRegD <= rD;

		if      (RESET)		FlagSelect <= 0;
		else if (`PHASE1)	FlagSelect <= IR[11:8];

		if      (RESET)									RegIR <= 0;
		else if (`PHASE1)								RegIR <= IR;
		else if ((`PHASE2 | `PHASE3) & `OP_COND_ASG)	RegIR <= {OpCode, rS, rS, rT};
	end


	//
	// Program Counter: PC
	//

	reg	PCinc, PCflag;	// Auxiliary

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
			if      (`PHASE3 & `OP_CALL)	NextPC <= (AbsAddr << Model);	// CALL or GOTO
			else if (`PHASE3 & `OP_RET)		NextPC <= RegOut [19:8];		// RET
			else							NextPC <= PCadder[12:1];		// Others

			PCinc	<= (`PHASE0) | (`PHASE2 & (rT == 0) & `OP_ALUMAC);		// OpFetch or K used

			PCflag  <= `PHASE2 & `OP_JP & Flag;								// '1' if relative jump
		end
	end

	assign PC = NextPC[Model+7:0];		// The logic not used is optimized away


	//
	// Bank of 16 Internal 24-bit Registers: r0-r15
	//

	reg  [23:0]	RegsBank[0:15];			// Register Bank Memory
	reg   [3:0]	RegAddr;				// Register Bank Address

	wire RegWE = (`PHASE0 & `OP_ALU)	// ALU operation
			   | (`PHASE0 & `OP_IN)		// INport command
			   | (`PHASE1 &  OldMAC)	// MAC operation
			   | (`PHASE3 & `OP_CALL);	// CALL command

   	always @(posedge CLK or posedge RESET)
	begin
		if (RESET)	RegAddr <= 0;
		else case (State)
			st0:	RegAddr <= OldRegD;		// Destination for MAC
			st1:	RegAddr <= IR[7:4];		// First Operand (rS)
			st2:	RegAddr <= rT;			// Second Operand (rT)
			st3:	RegAddr <= rD;			// Destination for ALU
		endcase
	end

	always @(posedge CLK)
	begin
		if (RegWE)
			RegsBank[RegAddr] <= DataBus;	// Sync Write from DataBus
	end
	assign RegOut = RegsBank[RegAddr];		// Async Read

	always @(posedge CLK or posedge RESET)	// Sync Register Output
	begin
		if (RESET)	ACC <= 0;
		else 		ACC <= RegOut;
	end


	//
	// ALU
	//

	wire [23:0]	ALUmac, ALUlogic, ALUarith;	// ALU outputs

	wire [23:0]	RegS = (rS == 0) ? 24'h000000  : ACC;		// rS or 0
	wire [23:0]	RegT = (rT == 0) ? {IR, 8'h00} : RegOut;	// rT or K

	// Input registers: receive two 24-bit operands S and T
	reg  [23:0]	OpA, OpB;
	always @(posedge CLK)
	begin
		OpA <= (State == st3) ? RegS : {OpA[3:0],OpA[23:4]};	// Loads S and shifts it for MAC
		OpB <= (State == st3) ? RegT : OpB;						// Loads T and keeps it for MAC
	end

	// Logic ALU
	`define	OP_AND	2'b00
	`define	OP_OR 	2'b01
	`define	OP_NOR	2'b10
	`define	OP_XOR	2'b11

	assign ALUlogic = OpCode[1:0] == `OP_AND ?   OpA & OpB
	                : OpCode[1:0] == `OP_OR  ?   OpA | OpB
	                : OpCode[1:0] == `OP_NOR ? ~(OpA | OpB)
	                :                            OpA ^ OpB;

	// Arithmetic ALU
	wire		aluCarry;
	wire [23:0] AddA = ((OpCode[1] | ~Flag) ? OpA : 24'h000000);
	wire [23:0] AddB = ((OpCode[1] |  Flag) ? OpB : 24'h000000);

	assign {aluCarry, ALUarith} = OpCode[0] ? (AddA - AddB) : (AddA + AddB);

	wire ALUoverflow = (aluCarry ^ ALUarith[23] ^ AddA[23] ^ AddB[23]);	// Overflow Flag
																		// Thanks Jan Gray

	//
	// Multiplier and Accumulator (16-bit fixed point, extended to 24 bits)
	//

	wire    [3:0]	InA = OpA[11:8];	// First operand input (four rotating bits of rS, or 0)
	wire   [15:0]	InB = OpB[23:8];	// Second operand input (rT or K)

	// First adder
	wire   [17:0]	Op1 = (InA[0] ? {InB[15], InB[15], InB} : 18'h00000);
	wire   [17:0]	Op2 = (InA[1] ? {InB[15], InB, 1'b0   } : 18'h00000);
	wire   [17:0]	Op3 = Op1 + Op2;

	// Second adder
	wire   [18:0]	Op4 = (InA[2] ? {InB[15], InB[15], InB, 1'b1} : 19'h00001);
	wire   [18:0]	Op5 = (State == st3)
					    ? (InA[3] ? {~InB[15], ~InB, 2'b11} : 19'h00000)
					    : (InA[3] ? { InB[15],  InB, 2'b00} : 19'h00000);
	wire   [18:0]	Op6 = Op4 + Op5;

	// Third adder (registered) and final result (valid only during ph1)
	reg    [19:0]	Op7;
	reg    [31:0]	AxB;
	reg     [1:0]	OldCode;

	// Acumulates and shifts. Null on new op.
	wire   [31:0]	Op8 = (State == st1) ? 32'h00000000
					    : {AxB[31], AxB[31], AxB[31], AxB[31], AxB[31:4]};

	always @(posedge CLK)
	begin
		Op7 <= {Op3[17], Op3[17], Op3} + {Op6[18:1], 2'b00};
		AxB <= Op8 + {Op7, 12'h000};
		OldCode <= (State == st1) ? OpCode[1:0] : OldCode;
	end

	// Final result selector and accumulator. Needs OpCode of former instruction.
	wire x;
	wire [23:0] AccA = (OldCode[1]) ? RegOut : 24'h000000;		// Acumulates for 011x, but not for 010x
	wire [23:0] AccB = (OldCode[1:0] == 2'b01) ? AxB[23:0]		// Multiply in 8,8 format               for 0101
					 : (~OldCode[0])           ? AxB[30:7]		// or in 1,15 format with addition      for 01x0
					 :                          ~AxB[30:7];		// or in 1,15 formtat with substraction for 0111
	assign {ALUmac,x} = {AccA, 1'b1} + {AccB, OldCode[0]};		// MAC unit does not modify any flag!

//	wire x, macCarry;
//	assign {macCarry, ALUmac,x} = {AccA, 1'b1} + {AccB, OldCode[0]};
//	wire MACoverflow = (macCarry ^ ALUmac[23] ^ AccA[23] ^ AccB[23]);		// MAC Overflow Flag?



	//
	// Internal Data Bus
	//

	assign  DataBus = (`PHASE0 & `OP_ARITH)	? ALUarith	   : 24'bz;	// Arithmetic operation
	assign  DataBus = (`PHASE0 & `OP_LOGIC)	? ALUlogic	   : 24'bz;	// Logic operation
	assign  DataBus = (`PHASE1)				? ALUmac	   : 24'bz;	// MAC operation
	assign  DataBus = (`PHASE3 | `PHASE2)	? { PC, 8'h00} : 24'bz;	// Return Address on CALLs
	assign  DataBus = (`PHASE0 & `OP_CTRL)	? {DIN}        : 24'bz;	// External input
	assign  DataBus = (`PHASE0 & `OP_MAC)	? 24'hFFFFFF   : 24'bz;	// Otherwise, pull-up


	//
	// Flags
	//

	`define	EQ	3'b000
	`define	NE	3'b001
	`define	OV	3'b010
	`define	NV	3'b011
	`define	LT	3'b100
	`define	LE	3'b101
	`define	GT	3'b110
	`define	GE	3'b111

	reg	ZFF, SFF, VFF;	// Internal flags: zero, sign and overflow.

	always @(posedge CLK or posedge RESET)
	begin
		if (RESET)
			{ZFF, SFF, VFF} <= 0;
		else if (`PHASE0)			// Updates flags on ALU and INPORT ops
		begin
			ZFF <= (DataBus == 0);	// One if null result
			SFF <= DataBus[23];		// One if negative result
			VFF <= ALUoverflow;		// One if overflow on add/sub
		end
	end

	always @(ZFF or SFF or VFF or FlagSelect)
	begin
		case (FlagSelect[2:0])
			`EQ:	Flag =  ZFF;		// equal (to zero)
			`NE:	Flag = ~ZFF;		// not equal (to zero)
			`OV:	Flag =  VFF;		// overflow
			`NV:	Flag = ~VFF;		// not overflow
			`LT:	Flag =  SFF & ~ZFF;	// less than (zero)
			`LE:	Flag =  SFF |  ZFF;	// less or equal (to zero)
			`GT:	Flag = ~SFF & ~ZFF;	// greater than (zero)
			`GE:	Flag = ~SFF |  ZFF;	// greater or equal (to zero)
		endcase
	end


	//
	// External Interface: 128 I/O ports
	//

	reg  [7:0]	PORT;		// Port Address Register
	reg			IOR, IOW;

	always @(posedge CLK or posedge RESET)
	begin
		if (RESET)
			PORT <= 0;
		else if (`PHASE2)
		begin
`ifdef LOW_POWER
		    if (`OP_IO)							// Only changes when used
`endif
				PORT <= IOaddr;					// I/O address for OUT and IN operations
		end

		if (RESET)	IOW <= 0;
		else		IOW <= `PHASE3 & `OP_OUT;	// On the first subcycle

		if (RESET)	IOR <= 0;
		else		IOR <= `PHASE3 & `OP_IN;	// On the first subcycle
	end

	assign	DOUT = RegOut[23:8];   
	assign  DOUT24 = RegOut;

endmodule	// DSPuva16

