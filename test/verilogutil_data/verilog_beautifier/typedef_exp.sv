package my_pkg;

  // Align declaration
  localparam uint MY_PARAM0 = 7  ;
  localparam uint PARAM1    = 127;
  localparam uint P1 = 1,
    int P2 = -3,
    bit [3:0] P3 = 4;


  // Block {}
  typedef struct packed {
    logic [2:0]  mode   ;
    my_subtype_u subtype;
  } my_type_t;

  // Block {} with other indent style
  typedef union
  {
    my_subtype_0_t    f0    ;
    my_subtype_f1_t   field1;
    my_subtype_test_t test  ;
  } my_subtype_u;

  // enum align
  typedef enum logic [2:0] {
    STATE_0,
    STATE_F0,
    STATE_244,
    STATE_DEFAULT
  } my_subtype_0_t;

  // function align
  function automatic my_subtype_0_t get_subtype_0 (input uint cnt, input uint data);
    get_subtype_0.subtytpe = (1<<cnt) + data;// comment0
    get_subtype_0.mode = get_subtype_0 + 1;
    get_subtype_0.f0 = ~get_subtype_0 - cnt;     // blabla 1
  endfunction

  // Embedded struct assignment
  protected const t_my_struct c_struct_init = '{
    enable        : 1,
    type_name     : "my_name",
    cfg_type_name : "config",
    my_dict       : '{"key0": "value0",
      "key16" : "module"},
    comp_mode     : my_other_pkg::COMP_MODE,
    mode          : my_other_pkg::DEFAULT_MODE
  };

  logic     [4:0]      var0;
  u8_t      [4:0]      var1;
  my_type_t [4:0][2:0] var2;
  my_type2_t           var3;


  import "DPI-C" pure function real cos  (input real a);
  import "DPI-C" pure function real sin  (input real a);
  pure virtual function foo();
  export "DPI-C" function dpi_report_error;
  export "DPI-C" function dpi_report_warning;

endpackage
