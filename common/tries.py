
class Letter:
    def __init__(self, letter):
        self.letter = letter
        self.child = {}
        self.eow = False

class Trie:
    def __init__(self):
        self.root = Letter('*')
        self.mn_prefix_len = float('inf')

    def __del__(self):
        pass

    def insert(self, word: str) -> None:
        cur = self.root
        idx = 0
        for ch in word:
            if ch not in cur.child:
                cur.child[ch] = Letter(ch)
            cur = cur.child[ch]
            idx += 1

        self.mn_prefix_len = min(self.mn_prefix_len, idx)
        cur.eow = True

    def search(self, word: str) -> bool:
        cur = self.root
        for ch in word:
            if ch not in cur.child:
                return False
            cur = cur.child[ch]

        return True if True == cur.eow else False

    def starts_with(self, prefix: str) -> bool:
        cur = self.root
        for ch in prefix:
            if ch not in cur.child:
                return False
            cur = cur.child[ch]
        return True

    def is_registered_suffix_exist(self, word: str) -> bool:
        violate_suffix = ''
        cur = self.root
        idx = 0
        for ch in word:
            if ch not in cur.child:
                break
            cur = cur.child[ch]
            violate_suffix += ch
            idx += 1

        return (True, violate_suffix) if self.mn_prefix_len == idx else (False, '')
