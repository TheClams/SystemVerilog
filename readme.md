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
 * Module instantiation:
 * Smart Autocompletion: method for standard type,  field for struct/interface, system task, ...
 * Alignment of block of code: support module port declaration and module instantiation (Palette command "Verilog: Alignment")
 * Toggle .* in module binding (similar to the auto-star feature of Emacs verilog-mode)
 * 'begin end' macro to surround a text by begin/end (cf Keymapping section to see how to use it)

####Configuration
To see all existing configuration option, go to Preferences->Package Settings->SystemVerilog->Settings (Default).

To edit settings open the Settings (User), and add parameter with the value you want.



Smart always snippets
---------------------
####Description
The snippets for the always block are context dependant and configurable:

 - always ff, always comb, always latch are specific to file with extension .sv
 - Signal name for clk, clk_en and reset (low and high) can be configured (see below).
 - The clock enable part of the snippets will be present only if the a signal with the correct name has been declared


The name for clk and reset can be extracted from the current buffer:

 - if the default clock name is not found in any posedge signal_name list, the highest occurence of a signal with a c in its name will be used
 - if the default reset low name is not found in any negedge signal_name list, the highest occurence of will be used
 - if the default reset high name is not found in any posedge signal_name list, the highest occurence of a signal without a c in its name will be used

The automatic extraction of the name will not be perfect in all cases, but it will always be better than the basic behavior


####Configuration
"sv.clk_name" : Clock name, default to "clk".

"sv.rst_n_name" : Reset active low,  default to "rst_n"

"sv.rst_name": Reset active high, default to "rst".

"sv.always_name_auto": Boolean to enable clk/rst name auto extraction, default to true

"sv.always_sv_only": Boolean to filter simple always in .sv files, default to true.

"sv.clk_en_name": Clock enable name, default to "clk_en"

"sv.always_ce_auto" : Boolean to insert the clock enable part only if the clk enable has been declared



Module Instantiation
---------------------
####Description
Use palette command "Verilog: Instantiate Module" or use keybinding to function 'verilog_module_inst'.

This open the palette with all verilog file (*.v, *.sv): select one and the instantiation will be inserted in the buffer.

If the module has some parameter you can enter the value of each parameter one by one: if the default value is good you can directly press enter

If autoconnection is enabled, signal with same name as port will be used as connection.
If they have not been declared, the signal declaration will also be added.
Location of signal declaration is configurable:
 - Just above module instantiation
 - First empty line after a start pattern
 - Last empty line between a start and an end pattern

Options allows to extend search to a signal matching port name with a prefix (ending with _) or a suffix (stating with _).
In case of multiple match, if one prefix/suffix is contained in the instance name it will be selected,
otherwise the first one will be used.

####Configuration
"sv.fillparam": On module instantiation with parameter user is asked a value for each parameter. Default to true.

"sv.autoconnect": Control if signals are created and connected in module instantiation. Default to true.

"sv.autoconnect_allow_prefix": True to expand search for signal to \w+_port. Default to true.

"sv.autoconnect_allow_suffix": True to expand search for signal to port_\w+. Default to true.

"sv.instance_prefix": Prefix to the module instantiation name, default to "i_".

"sv.instance_suffix": Suffix to the module instantiation name, default to "" (no suffix).

"sv.decl_indent": Number of indentation level for signal declaration, default to 1.

"sv.decl_start": Pattern to find for start of signals auto-declaration . Empty string to get declaration just above instantiation. Default to "Signals declaration".

"sv.decl_end": Pattern to find just after start to insert signal declaration before. Empty string to use first empty line after start pattern. Default to "/*----"



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
