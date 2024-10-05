import re


def get_valid_filename(s):
    dictionary = {">": "gt", "<": "lt"}
    s = str(s).strip().replace(" ", "_")
    pattern = re.compile("|".join(sorted(dictionary.keys(), key=len, reverse=True)))
    result = pattern.sub(lambda x: dictionary[x.group()], s)
    return result
