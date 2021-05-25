from syntax_parser.syntax_parser import *
from syntax_parser.syntax_parser_hpp import *
from syntax_parser.syntax_parser_cpp import *


class SyntaxParserFactory:
    def __init__(self):
        pass

    def __del__(self):
        pass
    
    @staticmethod
    def createCppHeader():
        return CppHeaderParser('CppHeaderParser')

    @staticmethod
    def createCppImpl():
        return CppImplParser('CppImplParser')
    
    creator = {}
    creator['hpp'] = createCppHeader.__func__
    creator['cpp'] = createCppImpl.__func__

    @staticmethod
    def get_supported_types():
        types = []
        for ctor in SyntaxParserFactory.creator:
            types.append(ctor)
        return types

    @staticmethod
    def create(extension):
        if extension not in SyntaxParserFactory.creator:
            return None
        return SyntaxParserFactory.creator[extension]()
