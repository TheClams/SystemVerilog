module add1(
    input a,
    output b);
    assign b = a;
    m_name0 inst0(d,f);
    m_name1  inst1  (  d , f ) ;
    m_name0 inst2 (.i1(i1), .i2(i2));
    m_name3 inst3 (
    .i1(i1),
     .i2(i2)
     );
    m_name4  inst4  (
    d,
    f);
    m_name5 #(p1, p2) inst5 (i1, i2);
    m_name6 #(
    .p1(p1),
    .p1(p2))inst6(
    .i1(i1),
    .i2(i2));
endmodule