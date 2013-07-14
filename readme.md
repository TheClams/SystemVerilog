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
		]
    }

