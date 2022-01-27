import os
import collections
import sys
from enum import Enum
import json
from util.platform_info import *


class ReturnType(Enum):
    SUCCESS = 0
    FILE_OPEN_ERR = 1
    UNICODE_ERR = 2


class FileType(Enum):
    CPP_HEADER = 1
    CPP_IMPL = 2
    JAVASCRIPT = 3
    PYTHON = 4
    JSON = 5
    TEXT = 6
    PRO = 7
    QML = 8


class UtilFile:
    def __init__(self):
        pass

    def __del__(self):
        pass

    file_types = collections.defaultdict(None)
    file_names = collections.defaultdict(None)

    @staticmethod
    def find_subdirs(url, depth=None):
        q = [(url, 0)]
        dirs = [url]

        limit = depth if depth else float('inf')

        while q:
            url, depth = q.pop(0)
            try:
                dir_names = os.listdir(url)
            except FileNotFoundError:
                print('ERROR: no such a url = {}'.format(url))
                continue
            except NotADirectoryError:
                print('ERROR: not a directory = {}'.format(url))
                continue

            for dir_name in dir_names:
                full_url = os.path.join(url, dir_name)
                if os.path.isdir(full_url) and depth + 1 <= limit:
                    q += (full_url, depth + 1),
                    dirs += full_url,

        return dirs

    @staticmethod
    def set_file_type_name(file_type, file_ext_name):
        UtilFile.file_types[file_ext_name] = file_type
        UtilFile.file_names[file_type] = file_ext_name

    @staticmethod
    def init_file_type():
        UtilFile.set_file_type_name(FileType.CPP_HEADER, 'h')
        UtilFile.set_file_type_name(FileType.CPP_HEADER, 'hpp')
        UtilFile.set_file_type_name(FileType.CPP_HEADER, 'hxx')
        UtilFile.set_file_type_name(FileType.CPP_IMPL, 'cpp')
        UtilFile.set_file_type_name(FileType.CPP_IMPL, 'cxx')
        UtilFile.set_file_type_name(FileType.CPP_IMPL, 'c')
        UtilFile.set_file_type_name(FileType.JSON, 'json')
        UtilFile.set_file_type_name(FileType.TEXT, 'txt')
        UtilFile.set_file_type_name(FileType.PRO, 'pro')
        UtilFile.set_file_type_name(FileType.QML, 'qml')

    @staticmethod
    def get_file_type(extension):
        UtilFile.init_file_type()
        return UtilFile.file_types[extension]

    @staticmethod
    def get_all_files(url, extension_filter):
        """
        find all the files to check
        """
        res = []
        try:
            file_list = os.listdir(url)
        except FileNotFoundError:
            print('ERROR: no such a url = {}'.format(url))
            return
        except NotADirectoryError:
            print('ERROR: not a directory = {}'.format(url))
            return

        for file in file_list:
            extension = file.split('.')[-1]
            if extension not in extension_filter:
                continue

            full_filename = os.path.join(url, file)
            res += (full_filename, UtilFile.get_file_type(extension)),

        return res

    @staticmethod
    def get_all_files_with_filter(url, extension_filter, file_filter):
        """
        find all the files to check
        """
        res = []
        try:
            file_list = os.listdir(url)
        except FileNotFoundError:
            print('ERROR: no such a url = {}'.format(url))
            return
        except NotADirectoryError:
            print('ERROR: not a directory = {}'.format(url))
            return

        for file in file_list:
            extension = file.split('.')[-1]
            if file not in file_filter and extension not in extension_filter:
                continue

            full_filename = os.path.join(url, file)
            res += (full_filename, UtilFile.get_file_type(extension)),

        return res

    @staticmethod
    def get_files(url, is_resursive, depth, extension_filter = ['h', 'hpp', 'cpp', 'c']):
        """
        OUT
            {"dir1" : [("file1", type1), ("file2", type2)], "dir2" : ...}
        """
        # get all the sub dires
        dirs = UtilFile.find_subdirs(url, depth) if is_resursive else [url]
        files = collections.defaultdict(list)

        for directory in dirs:
            ret = UtilFile.get_all_files(directory, extension_filter)
            if not ret:
                continue
            files[directory] += ret

        return files

    @staticmethod
    def get_files_with_filter(url, is_resursive, 
        file_filter, extension_filter = ['h', 'hpp', 'cpp', 'c']):
        """
        OUT
            {"dir1" : [("file1", type1), ("file2", type2)], "dir2" : ...}
        """
        # get all the sub dires
        dirs = UtilFile.find_subdirs(url) if is_resursive else [url]
        files = collections.defaultdict(list)

        for directory in dirs:
            ret = UtilFile.get_all_files_with_filter(
                directory, extension_filter, file_filter)
            if not ret:
                continue
            files[directory] += ret

        return files

    @staticmethod
    def filter_files(file_list, ext_to_handle = ['h', 'hpp']):
        files_to_handle = []
        for file in file_list:
            ext = file.split('.')[-1].lower()
            if ext not in ext_to_handle:
                continue

            files_to_handle += (file, ext),

        return files_to_handle

    @staticmethod
    def read_json(url):
        delimeter = PlatformInfo.get_delimiter()
        res = None
        cfg_request = os.path.dirname(os.path.realpath(__file__)) + delimeter + url
        with open(cfg_request) as fp:
            res = json.load(fp)

        return res

    @staticmethod
    def read_json_at_cur_dir(url):
        with open(url) as fp:
            res = json.load(fp)

        return res

    @staticmethod
    def get_dirs_files(directory, is_resursive, depth, extension_filter):
        dirs = []
        if directory.startswith('[') and directory.endswith(']'):
            for dir in directory[1:-1].split(','):
                dirs += dir.strip(),
        else:
            dirs += directory,

        UtilFile.init_file_type()
        ret_dir_files = collections.defaultdict(list)
        for directory in dirs:
            #print(directory)
            dir_files = UtilFile.get_files(directory, is_resursive, depth, extension_filter)

            for directory, files in dir_files.items():
                ret_dir_files[directory] += files

        return ret_dir_files

    @staticmethod
    def get_dirs_files_with_filter(directory, is_resursive, extension_filter, file_filter):
        ret_dir_files = collections.defaultdict(list)
        dir_files = UtilFile.get_files_with_filter(
            directory, is_resursive, file_filter, extension_filter)
        for directory, files in dir_files.items():
            ret_dir_files[directory] += files

        return ret_dir_files

    @staticmethod
    def get_content(url):
        lines = None
        if os.path.isdir(url):
            return None

        with open(url, 'r', encoding='utf8') as f:
            try:
                lines = f.readlines()
            except UnicodeDecodeError as e:
                print(e)
                return None

        return ''.join(lines)

    @staticmethod
    def open_file(url, encoding='UTF8'):
        try:
            fp = open(url, 'r', encoding=encoding)
        except FileNotFoundError as e:
            print(e, 'for ', url)
            return None
        except IsADirectoryError as e:
            print(e, 'for ', url)
            return None
        except PermissionError as e:
            print(e, 'for ', url)
            return None

        return fp

    @staticmethod
    def get_lines(url, lines, encoding='utf-8'):
        fp = UtilFile.open_file(url, encoding)
        if not fp:
            return ReturnType.FILE_OPEN_ERR

        try:
            lines += fp.readlines()
        except UnicodeDecodeError as e:
            #print('UnicodeDecodeError:', e, 'for ', url)
            fp.close()
            return ReturnType.UNICODE_ERR

        fp.close()
        return ReturnType.SUCCESS
    
    @staticmethod
    def save_as_file(url, data):
        try:
            with open(url, 'w') as fp:
                fp.write(data)
        except:
            return False    
        
        return True

    @staticmethod
    def get_extension_name(file_type: FileType):
        return UtilFile.file_names[file_type]

    @staticmethod
    def get_extension(name):
        delimeter = PlatformInfo.get_delimiter()
        tokens = name.split(delimeter)
        if not tokens:
            return ''

        tokens = tokens[-1].split('.')
        if not tokens:
            return ''

        return tokens[-1]

