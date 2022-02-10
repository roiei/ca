from syntax_parser.syntax_parser import *
from syntax_parser.syntax_parser_hpp import *
from syntax_parser.syntax_parser_cpp import *


class SyntaxParserFactory:
    def __init__(self):
        pass

    def __del__(self):
        pass
    
    @staticmethod
    def createCppHeader(ctx=None):
        return CppHeaderParser('CppHeaderParser', ctx)

    @staticmethod
    def createCppImpl(ctx=None):
        return CppImplParser('CppImplParser', ctx)
    
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
    def create(extension, ctx=None):
        if extension not in SyntaxParserFactory.creator:
            return None
        return SyntaxParserFactory.creator[extension](ctx)

    @staticmethod
    def get_parsers(extensions=[], ctx=None):
        res = {}
        for extension in extensions:
            res[extension] = SyntaxParserFactory.create(extension, ctx)
        return res
