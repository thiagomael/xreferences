#coding=utf-8

from dependency_graph import *


# Parser :: line -> DependencyGraph -> Parser

def log(*args):
    print args

def parse_pvs(lines):
    parser = default_parser
    dependency_graph = DependencyGraph()

    for line in lines:
        new_parser = parser(line, dependency_graph)
        if new_parser is not None:
            parser = new_parser

    return dependency_graph


def parse_imports_begin(line, dependency_graph):
    importing_keyword = "IMPORTING"
    index = line.find(importing_keyword)
    if index >= 0:
        log(u"Beginning imports")
        _parse_imports(line[index+len(importing_keyword):],
                       dependency_graph)
        return parse_imported_theories
    return None


def parse_imported_theories(line, dependency_graph, imports):
    stripped = line.strip()
    if len(stripped):
        _parse_imports(stripped,
                       dependency_graph)
        return parse_imported_theories
    else:
        return parse_imports_begin

def _parse_imports(line, dependency_graph):
    dependency_graph.add_
    pass
