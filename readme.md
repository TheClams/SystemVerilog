Sublime Text SystemVerilog Package
==================================


Description
-----------

#### Syntax Highlighting:
 * SystemVerilog / Verilog
 * UCF (Xilinx Constraint file)

Note: the default color scheme (Monokai) is missing a lot of scope, and might not give the best results.
You can try my personal variation of Sunburst : https://gist.github.com/TheClams/5811d7bc8829abe58c11d4c98e729dc0

#### Code Navigation:

 * Show signal declaration in tooltip or status bar
 * Goto declaration : move cursor to the declaration of the selected signal
 * Goto driver : select a signal a go to the driver (port, assignement, connection)
 * Find Instances: find all instance of a module inside a project
 * Move cursor / select text between start/end of block (like [], {}, begin/end, function/endfunction, ...)
 * Show hierarchy of a module (all its sub-module)
 * Navigation side-bar:
   - Displaying a class members/method, module port/signal/instances, ...
   - Double click on instance/type to jump to it

#### Code Completion :

 * Smart Autocompletion: method for standard type,  field for struct/interface/class, system task, ...
 * Smart snippet for always, case
 * 'begin end' macro to surround a text by begin/end (cf Keymapping section to see how to use it)
 * Various Snippets (module, interface, class, for, ...)
 * Insert template for FSM

#### Module Instance helper:

 * Instantiation: Select a module from a list and create instantiation and connection
 * Reconnect: remove connection to deleted port, add connection to new port
 * Toggle .* in module binding (similar to the auto-star feature of Emacs verilog-mode)

#### Code Alignement:

 * Reindent
 * Align module port
 * Align signal declaration
 * Align module instantiation
 * Align assignement

#### Linting:
 * Find/Remove all unused signals
 * List all undeclared signals

#### Configuration
To see all existing configuration option and edit your configuration, go to Preferences->Package Settings->SystemVerilog->Settings.


#### Detail documentation
For a detail documentation on the different features, check online documentation: http://sv-doc.readthedocs.org/en/latest .



Keymapping example
------------------

To map key to the different features, simply add the following to your user .sublime-keymap file:

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
			{ "key": "selector", "operator": "equal", "operand": "source.systemverilog"}
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
		"keys": ["alt+shift+a"], "command": "verilog_align", "args":{"cmd":"reindent"},
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
	{
		"keys": ["ctrl+m"], "command": "verilog_goto_block_boundary", "args":{"cmd":"move"},
		"context":
		[
			{ "key": "num_selections", "operator": "equal", "operand": 1 },
			{ "key": "selector", "operator": "equal", "operand": "source.systemverilog"}
		]
	},
	{
		"keys": ["ctrl+shift+m"], "command": "verilog_goto_block_boundary", "args":{"cmd":"select"},
		"context":
		[
			{ "key": "num_selections", "operator": "equal", "operand": 1 },
			{ "key": "selector", "operator": "equal", "operand": "source.systemverilog"}
		]
	},
	{ "keys": ["f1"], "command": "verilog_toggle_navbar", "args":{"cmd":"toggle"}},
	{ "keys": ["ctrl+f1"], "command": "verilog_toggle_lock_navbar"},
	{
	  "keys": ["alt+f1"], "command": "verilog_show_navbar",
	  "context":[{ "key": "selector", "operator": "equal", "operand": "source.systemverilog"}]
	}

