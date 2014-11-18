Sublime Text SystemVerilog Package
==================================


Description
-----------

####Syntax Highlighting:
 * SystemVerilog
 * UCF (Xilinx Constraint file)

####Various snippets:
 * module
 * class
 * always block
 * case
 * function/task
 * ...

####Features:
 * Show signal declaration in status bar
 * Module instantiation:
   > Use palette command "Verilog: Instantiate Module" or use keybinding to function 'verilog_module_inst'.
   > This open the palette with all verilog file (*.v, *.sv): select one and the instantiation with empty connection will be created.
   > Look at setting file (Preferences->Package settings->SystemVerilog) to configure options
 * Smart Autocompletion: method for standard type or field of struct/interface (triggered by .), system task (triggered by $), ...
 * Alignment of block of code: support module port declaration and module instantiation (Palette command "Verilog: Alignment")
 * Macro to insert a begin end around a selection (cf Keymapping section to see how to use it)



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
	},
	{
		"keys": ["ctrl+f10"], "command": "verilog_module_inst",
		"context":
		[
			{ "key": "num_selections", "operator": "equal", "operand": 1 },
			{ "key": "selector", "operator": "equal", "operand": "source.systemverilog"}
		]
	},
	{
		"keys": ["ctrl+shift+a"], "command": "verilog_align",
		"context":
		[
			{ "key": "num_selections", "operator": "equal", "operand": 1 },
			{ "key": "selector", "operator": "equal", "operand": "source.systemverilog"}
		]
	},
	// Begin/End
	{
		"keys": ["ctrl+'"],
		"command": "insert_snippet", "args": {"contents": "begin\n\t$0\nend"},
		"context": [{ "key": "selection_empty", "operator": "equal", "operand": true, "match_all": true }]
	},
	{
		"keys": ["ctrl+'"],
		"command": "run_macro_file",
		"args": {"file": "Packages/SystemVerilog/beginend.sublime-macro"},
		"context": [{ "key": "selection_empty", "operator": "equal", "operand": false, "match_all": true }]
	},
