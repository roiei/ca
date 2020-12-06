import collections
import re


class SearchPatternCpp:
    def __init__(self):
        pass

    def __del__(self):
        pass

    patterns = collections.defaultdict(None)

    @staticmethod
    def reset_patterns(clz):
        SearchPatternCpp.patterns['copy_const'] = re.compile('{}\s*\((const)*(\s)*{}(\s)*&(\s)*[\w]*(\s)*\)(\s)*(=)*(\s)*(delete|default)*;'.format(clz, clz))
        SearchPatternCpp.patterns['move_const'] = re.compile("{}\s*\((const)*(\s)*{}(\s)*&&(\s)*[\w]*(\s)*\)(\s)*(noexcept)*(\s)*(=)*(\s)*(delete|default)*(\s)*;".format(clz, clz))
        SearchPatternCpp.patterns['move_assign'] = re.compile('(const(\s)*)*{}[\s]*&[\s]*operator[\s]*=[\s]*\((const)*[\s]*{}(\s)*&&(\s)*[\w]*(\s)*\)(\s)*((noexcept)*(\s)*=)*(\s)*[\w]*(\s)*;'.format(clz, clz))
        SearchPatternCpp.patterns['copy_assign'] = re.compile('(const(\s)*)*{}[\s]*&[\s]*operator[\s]*=[\s]*\((const)*[\s]*{}(\s)*&(\s)*[\w]*(\s)*\)(\s)*((noexcept)*(\s)*=)*(\s)*[\w]*(\s)*;'.format(clz, clz))
        SearchPatternCpp.patterns['destructor'] = re.compile('~{}[\s]*\(\)'.format(clz))
        #SearchPatternCpp.patterns['method'] = re.compile('(static|virtual)*(const)*\s*[\w\s,<>:~]+\s*\**&*\s*\s*~*(\w)*\s*(=|==)*\s*\([\w\d=,\s&\:<>*]*\)\s*(override|noexcept|const)*(\s*=\s*)*0*(delete)*(\s*=\s*)*(default)*\s*;*')
        
    @staticmethod
    def init_default_patterns():
        SearchPatternCpp.patterns['singleton'] = re.compile('static\s+[\w]+\s*(\*|&)\s*[\w]+(instance|Instance)\([\w]*\)\s*;')
        SearchPatternCpp.patterns['singleton_ptr'] = re.compile('static\s+[\w]+\s*\*\s*[\w]+(instance|Instance)\([\w]*\)\s*;')
        SearchPatternCpp.patterns['singleton_ptr'] = re.compile('static\s+[\w]+\s*\*\s*[\w]+(instance|Instance)\([\w]*\)\s*;')
        SearchPatternCpp.patterns['singleton_ref'] = re.compile('static\s+[\w]+\s*&\s*[\w]+(instance|Instance)\([\w]*\)\s*;')
        SearchPatternCpp.patterns['friend_class'] = re.compile('friend\s+class')
        SearchPatternCpp.patterns['friend_func'] = re.compile('friend\s+[^class]+[\w]+')
        SearchPatternCpp.patterns['protected'] = re.compile('protected\s*:')
        SearchPatternCpp.patterns['pure_virtual_function'] = re.compile('virtual([\w\s(:<>&*),]+)(=\s*0|PURE)\s*;')
        SearchPatternCpp.patterns['class_definition'] = re.compile('(enum\s*)*(class[\s]+)([\w]+)(\s)*(:)*(\s)*(public|protected|private)*(\s)*[\w]*(\s)*([\s\n]*{)')
        #SearchPatternCpp.patterns['class_definition'] = re.compile('(class[\s]+)([\w]+)(\s)*(:)*(\s)*(public|protected|private)*(\s)*[\w]*(\s)*([\s\n]*{)')
        SearchPatternCpp.patterns['curly_brace'] = re.compile('{[:\w\s~=<>&();]*}')
        SearchPatternCpp.patterns['method'] = re.compile('[~\w\s<,>():=*|+&!-]+\s*\(+[\w\s&*<:>=,()\"]*\)+[\w\s=]*')

    @classmethod
    def get_pattern_curly_brace(cls):
        return 'curly_brace', cls.patterns['curly_brace']

    @classmethod
    def get_pattern_methods(cls):
        return 'method', cls.patterns['method']

    @classmethod
    def get_pattern_class_def(cls):
        return 'class_definition', cls.patterns['class_definition']

    @classmethod
    def get_pattern_rof(cls):
        rules = ['copy_const', 'move_const', 'move_assign', 'copy_assign', 'destructor']
        return [(pname, pattern) for pname, pattern in cls.patterns.items() if pname in rules]

    @classmethod
    def get_pattern_friend(cls):
        rules = ['friend_class', 'friend_func']
        return [(pname, pattern) for pname, pattern in cls.patterns.items() if pname in rules]

    @classmethod
    def get_pattern_protected(cls):
        rules = ['protected']
        return [(pname, pattern) for pname, pattern in cls.patterns.items() if pname in rules]

    @classmethod
    def get_pattern_pure_virtualfunc(cls):
        return 'pure_virtual_function', cls.patterns['pure_virtual_function']

    @classmethod
    def get_pattern_singleton(cls):
        return 'singleton', cls.patterns['singleton']

    @classmethod
    def get_pattern_singleton_ptr(cls):
        rules = ['singleton_ptr']
        return [(pname, pattern) for pname, pattern in cls.patterns.items() if pname in rules]

    @classmethod
    def get_pattern_singleton_ref(cls):
        return 'singleton_ref', cls.patterns['singleton_ref']

    @staticmethod
    def get_search_pattern(keyword):
        """
            return: regex pattern
        """
        return SearchPatternCpp.patterns[keyword]
