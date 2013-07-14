import sublime, sublime_plugin
import re, string, os


class VerilogTypeCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        if len(self.view.sel())==0 : return;
        region = self.view.sel()[0]
        # If nothing is selected expand selction to word
        if region.empty() : region = self.view.word(region);
        s = self.get_type(self.view.substr(region))
        sublime.status_message(s)

    def get_type(self,var_name):
        #Find first line containing the variable name
        r = self.view.find('\\b'+var_name+'\\b',0)
        if r==None : return;
        r = self.view.line(r)
        # Extract type
        return self.view.substr(r)