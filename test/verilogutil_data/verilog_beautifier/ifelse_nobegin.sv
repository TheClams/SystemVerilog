always @ (posedge clk)
begin
for (g=0;g<10;g=g+1)
if(test)
a <= 1;
else
a <= 2;
end

always @ (posedge clk)
    begin
        case(test)
            SET1 :
                out_dat <= in_dat1;
            SET2 :
                begin
                    if(sel)
                        out_dat <= in_sel1;
                    else
                        out_dat <= in_sel2;
                end
            SET3 :
                if(sel2)
                    out_dat <= in_sel3;
                else
                    out_dat <= in_sel4;
            default :
                out_dat <= out_dat;
        endcase
end

always @ (posedge clk)
begin
if(sel10)
if(test)
a <= 1;
else
a <= 2;
else
for (i=0;i<10;i=i+1)
begin
    b[i] <= din[i];
end
end