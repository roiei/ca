
import json


class JSonSerializer:
    def __init__(self):
        pass

    def __del__(self):
        pass

    @staticmethod
    def serialize_to_json(data):
        with open("out.json", "w") as json_file:
            json.dump(data, json_file)

    @staticmethod
    def convert_to_dict(info):
        """
        OUT:
            {
                "dir1": [
                    "file1": [
                        "class1": [
                            "vio1",
                            "vio2"
                        ]
                    ]
                ],
                "dir2" ...
            }
        """
        mx_len = 50
        dirs = {}
        for d, files in info.items():
            d = '...' + d[-mx_len:]
            out_files = {}

            for file in files:
                out_clzs = {}
                file_name = '...' + file.get_name()[-mx_len:]

                for clz, violate_items in file.clzs.items():
                    out_violates = []

                    for violate in violate_items:
                        out_violates += violate,

                    out_clzs[clz] = out_violates

                out_files[file_name] = out_clzs

            dirs[d] = out_files

        # print(dirs)
        # for d, files in dirs.items():
        #     print('dir.', d)
        #     for file, clzs in files.items():
        #         print('file = ', file)
        #         for clz, vios in clzs.items():
        #             print('clz = ', clz)
        #             for vio in vios:
        #                 print(vio)
        #     print()

        return dirs


#JSonSerializer.serialize_to_json()
