package my_pkg;

   // One arg function
   function integer abs(input integer value);
      if (value >=0 ) begin
         return value;
      end
      else begin
         return -value;
      end
   endfunction : abs


   // Two args function with default value for one
   function automatic string join_string (ref string a[], input string c=".");
      string s;
      foreach (a[i]) begin
         if (i==0) s = a[i];
         else s = {s,c,a[i]};
      end
      return s;
   endfunction : join_string

endpackage
