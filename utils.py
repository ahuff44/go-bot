#!/usr/bin/env python

# from sys import stdin
# import collections as coll
# import operator as ops
# import itertools as itt
from functools import partial as curry
# import math
import re
# import random
# import sys
from pprint import pprint
# from fractions import Fraction as Frac
# from time import time

def nary(func):
    """ Turns a binary function into an n-ary function """
    def wrapped(*args):
        return reduce(func, args)
    return wrapped

@nary
def compose(f, g):
    return lambda *args, **kwargs: f(g(*args, **kwargs))

def pipeto(post):
    def decorator(func):
        def wrapped(*args, **kwargs):
            return post(func(*args, **kwargs))
        return wrapped
    return decorator

@pipeto(dict)
def grep(dictionary, grep_str):
    """ Filters a dictionary by only retaining keys that match the given regular expression
        Inspired by Ruby Enumerables' grep: http://ruby-doc.org/core-2.1.0/Enumerable.html#method-i-grep
        Example:
            > grep({"123abc": 10, "defghi": 20, "123xy": 30}, r"[a-z]{3}")
            {'123abc': 10, 'defghi': 20}
    """
    for key, val in dictionary.iteritems():
        if re.search(grep_str, key):
            yield key, val

def file_to_string(filename):
    with open(filename, "r") as file_:
        return '\n'.join(file_.readlines())

@nary
def dict_merge(a, b):
    res = a.copy()
    res.update(b)
    return res
