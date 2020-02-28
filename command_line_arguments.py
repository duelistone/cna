# command_line_arguments

'''Module to parse command line arguments.'''

import bisect

class cla_parser(object):
    def __init__(self, arg_list):
        self.argv = arg_list
        self.arg_list = arg_list[:]
        self.keyword_list = []
        self.parse_result = {}
        self.parse_complete = False

    def register(self, s, num_args, priority=1, remove_from_argv=False):
        bisect.insort(self.keyword_list, cla_keyword(s, num_args, priority, remove_from_argv))

    def parse(self):
        self.parse_result = {}
        arg_list = self.arg_list[:]
        for e in self.keyword_list:
            try:
                index = arg_list.index(e.name)
            except:
                continue
            if e.num_args >= 0:
                self.parse_result[e.name] = arg_list[index + 1:index + e.num_args + 1]
                del arg_list[index:index + e.num_args + 1]
                if e.remove_from_argv:
                    try:
                        index = self.argv.index(e.name)
                    except:
                        continue
                    del self.argv[index:index + e.num_args + 1]
            else:
                self.parse_result[e.name] = arg_list[index + 1:]
                del arg_list[index:]
                if e.remove_from_argv:
                    try:
                        index = self.argv.index(e.name)
                    except:
                        continue
                    del self.argv[index:]
                    
        self.parse_result[""] = arg_list[1:] # Remaining arguments
        self.parse_complete = True
    
    def __contains__(self, s):
        if self.parse_complete:
            return s in self.parse_result

    def args_for_keyword(self, s, enforce_num_args=False):
        if self.parse_complete and s in self.parse_result:
            if enforce_num_args:
                for k in self.keyword_list:
                    if k.name == s and k.num_args == len(self.parse_result[s]):
                        return self.parse_result[s]
            else:
                return self.parse_result[s]

    def get_leftover_args(self):
        return self.parse_result[""]

class cla_keyword(object):
    def __init__(self, name, num_args, priority, remove_from_argv=False):
        self.name = name
        self.num_args = num_args
        self.priority = priority
        self.remove_from_argv = remove_from_argv

    def __lt__(self, other):
        return self.priority <= other.priority
