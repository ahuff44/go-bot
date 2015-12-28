#!/usr/bin/env python

# from sys import stdin
# import collections as coll
# import operator as ops
import itertools as itt
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

flatten = itt.chain.from_iterable

class Either(object):
    # See http://hackage.haskell.org/package/base-4.8.1.0/docs/Data-Either.html

    def __init__(self, is_right, value):
        self.is_right = is_right
        self.value = value

    def __getitem__(self, key):
        if self.is_right:
            return self.value[key]
        else:
            # do nothing if this is an error object
            return self

    def fmap(self, if_right, if_left):
        if self.is_right:
            return Either(True, if_right(self.value))
        else:
            return Either(False, if_left(self.value))

    def fmap_right(self, op):
        return self.fmap(op, (lambda x: x))

    def fmap_left(self, op):
        return self.fmap((lambda x: x), op)

    def extract(self):
        if self.is_right:
            return self.value
        else:
            raise Exception(self.value)

    def __bool__(self):
        return is_right
    __nonzero__=__bool__

    def __str__(self):
        return "Either(%s, %s)"%(str(self.is_right), str(self.value))

    # TODO fix these? probably a better idea would be to implement >>= externally
    # def __getattribute__(self, name):
    #     if self.is_right:
    #         return self.value.__getattribute__(name)
    #     else:
    #         # do nothing if this is an error object
    #         return self

    # def __setattr__(self, name, value):
    #     if self.is_right:
    #         self.value.__setattr__(name, value)
    #     else:
    #         # do nothing if this is an error object
    #         pass

    @classmethod
    def from_response(klass, response):
        if response.ok:
            return Either(True, response.json())
        else:
            return Either(False, response)

