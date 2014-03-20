Sublime Text SystemVerilog Package
==================================


Description
-----------

Syntax Highlighting:
 - SystemVerilog
 - UCF (Xilinx Constraint file)

Various snippets: module, class, if/else, case, ...

Features:
 - Show signal declaration in status bar
 - Module instantiation
  * Use palette command "Verilog Instantiate Module" or use keybing to function 'verilog_module_inst'
  * This open the palette with all verilog file (*.v, *.sv): select one and the instantiation with empty connection will be created
 - hopefully more to come :P



Keymapping example
------------------

To map key to the different feature, simply add the following to your user .sublime-keymap file:

	{
		"keys": ["f10"], "command": "verilog_type",
		"context":
		[
			{ "key": "num_selections", "operator": "equal", "operand": 1 },
			{ "key": "selector", "operator": "equal", "operand": "source.systemverilog"}
		],
		"keys": ["ctrl+f10"], "command": "verilog_module_inst",
		"context":
		[
			{ "key": "num_selections", "operator": "equal", "operand": 1 },
			{ "key": "selector", "operator": "equal", "operand": "source.systemverilog"}
		]
	}

