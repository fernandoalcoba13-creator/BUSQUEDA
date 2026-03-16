from platforms import printables
from platforms import thingiverse
from platforms import cults3d
from platforms import myminifactory
from platforms import makerworld


def search(query, platforms):

    results = []

    if "printables" in platforms:
        try:
            results += printables.search(query)
        except Exception as e:
            print("printables error", e)

    if "thingiverse" in platforms:
        try:
            results += thingiverse.search(query)
        except Exception as e:
            print("thingiverse error", e)

    if "cults3d" in platforms:
        try:
            results += cults3d.search(query)
        except Exception as e:
            print("cults error", e)

    if "myminifactory" in platforms:
        try:
            results += myminifactory.search(query)
        except Exception as e:
            print("mmf error", e)

    if "makerworld" in platforms:
        try:
            results += makerworld.search(query)
        except Exception as e:
            print("makerworld error", e)

    return results
