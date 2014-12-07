Sublime Text SystemVerilog Package
==================================


Description
-----------

####Syntax Highlighting:
 * SystemVerilog / Verilog
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
 * Goto declaration : move cursor to the declaration of the selected signal
 * Goto driver : select a signal a go to the driver (port, assignement, connection)
 * Module instantiation: Select a module from a list and create instantiation and connection
 * Smart Autocompletion: method for standard type,  field for struct/interface, system task, ...
 * Insert template for FSM
 * Show hierarchy of a module
 * Alignment of block of code: support module port/signal declaration and module instantiation (Palette command "Verilog: Alignment")
 * Toggle .* in module binding (similar to the auto-star feature of Emacs verilog-mode)
 * 'begin end' macro to surround a text by begin/end (cf Keymapping section to see how to use it)

####Configuration
To see all existing configuration option, go to Preferences->Package Settings->SystemVerilog->Settings (Default).

To edit settings open the Settings (User), and add parameter with the value you want.

####Detail documentation
For a detail documentation on the different features, check (online documentation)[http://sv-doc.readthedocs.org/en/latest/].



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
		"keys": ["ctrl+shift+f10"], "command": "verilog_toggle_dot_star",
		"context":
		[
			{ "key": "num_selections", "operator": "equal", "operand": 1 },
			{ "key": "selector", "operator": "equal", "operand": "source.systemverilog meta.module.inst"}
		]
	},
	{
		"keys": ["ctrl+shift+a"], "command": "verilog_align",
		"context":
		[
			{ "key": "selector", "operator": "equal", "operand": "source.systemverilog"}
		]
	},
	{
		"keys": ["ctrl+f12"], "command": "verilog_goto_driver",
		"context":
		[
			{ "key": "num_selections", "operator": "equal", "operand": 1 },
			{ "key": "selector", "operator": "equal", "operand": "source.systemverilog"}
		]
	},
	{
		"keys": ["shift+f12"], "command": "verilog_goto_declaration",
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
