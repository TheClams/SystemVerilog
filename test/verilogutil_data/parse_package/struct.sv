package my_pkg;
    typedef struct {
        logic [3:0] atype;
        logic [lpq_sym_in_ch*4-1:0] data [pq_channel];
    } packet_t;
endpackage
