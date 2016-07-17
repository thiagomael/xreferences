#!/usr/bin/env python
#coding=utf-8
"""
Script to extract cross-references in a LaTeX document.
"""

from collections import defaultdict
from itertools import chain, product


class DependencyGraph(object):
    def __init__(self):
        self._adjacencies = defaultdict(set)
        self._nodes = set()
        self._node_names = dict()

    def add_dependency(self, dependent, dependency):
        if dependent != dependency: # Avoid cycles
            self._adjacencies[dependent].add(dependency)
            self._nodes.add(dependent)
            self._nodes.add(dependency)

    def add_custom_name(self, node_label, name):
        self._node_names[node_label] = name

    def subgraph(self, label):
        """
        Returns a new DependencyGraph without nodes unreachable from
        the one whose label is passed as an argument.
        """
        nodes = self._visit(label)
        new_graph = DependencyGraph()
        new_graph._adjacencies.update({node: self._adjacencies[node] for node in nodes})
        new_graph._nodes.update(nodes)
        new_graph._node_names = {label: name for label, name in self._node_names.iteritems() if label in nodes}
        return new_graph

    def to_dot(self):
        nodes = {node: "n"+str(i) for i, node in enumerate(self._nodes)}
        nodes_declaration = ['%s [texlbl="%s"];' % (id_, self._make_dot_label(node)) for node, id_ in nodes.iteritems()]

        exploded_dependencies = chain(*[product([dependent], dependencies) for dependent, dependencies in self._adjacencies.iteritems()])
        edges = ['%s -> %s;' % (nodes[dependent], nodes[dependency]) for dependent, dependency in exploded_dependencies]

        dot_template = r'''
digraph d {
    node [shape="none"];
    overlap="prism";
    ratio="auto";
    
    %s
    
    %s
}
        '''
        return dot_template % ('\n'.join(nodes_declaration),
                               '\n'.join(edges))

    def _visit(self, label):
        nodes = set([label])
        adjacencies = self._adjacencies[label]
        for adjacency in adjacencies:
            nodes.update(self._visit(adjacency))
        return nodes

    def _make_dot_label(self, node_tex_label):
        custom_label = self._node_names.get(node_tex_label)
        if custom_label is not None:
            return r"\hyperref[%s]{%s}" % (node_tex_label, custom_label)
            #return r"\Cref{%s}" % node_tex_label
        else:
            return r"\nameref{%s}" % node_tex_label


# Parser :: line -> DependencyGraph -> Parser

def log(*args):
    print args

def parse_tex(lines):
    parser = default_parser
    dependency_graph = DependencyGraph()

    for line in lines:
        new_parser = parser(line, dependency_graph)
        if new_parser is not None:
            parser = new_parser

    return dependency_graph


def parse_scope_begin(line, dependency_graph):
    scope_type = _parse_scope_type(line)
    if scope_type is not None:
        scope_description = _parse_scope_description(line)
        log("Beginning scope " + scope_type + str(scope_description))
        return lambda l, dg: parse_scope_label(l, dg, scope_type, scope_description)
    return None


def parse_scope_label(line, dependency_graph, scope_type, scope_description):
    label = _parse_scope_label(line)
    if label is None:
        raise Exception("A scope must always be followed by a label")
    log("Scope label: " + label)
    dependency_graph.add_custom_name(label, scope_description)
    return lambda l, dg: parse_scope_end(l, dg, scope_type, label)


def parse_scope_end(line, dependency_graph, scope_type, label):
    if _is_scope_end(line, scope_type):
        log("Ending scope %s (%s)" % (label, scope_type))
        return default_parser

    references = _parse_references(line, list())
    for reference in references:
        dependency_graph.add_dependency(label, reference)
    return None


def _parse_scope_type(line):
    scope_begin = r'\begin'
    if scope_begin in line:
        scope_type = _parse_brace_content(line)
        if scope_type in scope_delimiters:
            return scope_type
    return None


def _parse_scope_label(line):
    if r'\label' in line:
        label = _parse_brace_content(line)
        return label
    return None


def _parse_scope_description(line):
    return _parse_bracket_content(line)


def _parse_references(line, references_so_far):
    indices = [line.find(delimiter) for delimiter in reference_prefixes]
    first = _min_valid_index(*indices)
    if first >= 0:
        stop = _min_valid_index(line.find(',', first),
                                line.find('}', first))
        reference = line[first:stop]
        references_so_far.append(reference)
        return _parse_references(line[stop:], references_so_far)
    return references_so_far


def _min_valid_index(*indices):
    valid_indices = filter(lambda i: i>=0, indices)
    if len(valid_indices) > 0:
        return min(valid_indices)
    else:
        return -1


def _is_scope_end(line, scope_type):
    scope_end = r'\end{%s}' % scope_delimiters[scope_type]
    return scope_end in line


def _parse_brace_content(line):
    return _parse_between(line, '{', '}')


def _parse_bracket_content(line):
    return _parse_between(line, '[', ']')


def _parse_between(line, left_delimiter, right_delimiter):
    open_brace = line.find(left_delimiter)
    if open_brace == -1:
        return None
    close_brace = line.find(right_delimiter, open_brace)
    return line[open_brace+1:close_brace]

default_parser = parse_scope_begin


def dump(graph_dot, label):
    tikz_output = r"""
\begin{tikzpicture}[
        align=center,
        text centered,
        text width=80pt]
    \small
    \begin{dot2tex}[dot, codeonly]

        %s

    \end{dot2tex}
\end{tikzpicture}
    """
    sanitized_label = label.replace(':', '-')
    with open(sanitized_label+'.tikz', 'w') as out:
        out.write(tikz_output % graph_dot)


import fileinput

# Configuration
#------------------------------------------------

# We search from \begin{<key>} until \end{<value>}.
scope_delimiters = {"theorem": "proof",
                    "lemma": "proof",
                    "corollary": "corollary",
                    "definition": "definition"}

reference_prefixes = ["theorem:",
                      "lemma:",
                      "corollary:",
                      "def:"]
#------------------------------------------------

if __name__ == '__main__':
    # Ideally, these should come as command-line arguments.
    tex_files = ["/home/thiago/Projects/papers/reana-spl/main.tex"]
    subgraphs = [
            "theorem:feature-family-soundness",
            "theorem:feature-product-soundness",
            "theorem:family-product-soundness",
            "theorem:family-soundness",
            "theorem:feature-family-product-soundness"]

    dg = parse_tex(fileinput.input(tex_files))  # Concatenate files as if they were a single one
    dump(dg.to_dot(), "theory-structure")
    for subgraph_label in subgraphs:
        dump(dg.subgraph(subgraph_label).to_dot(), subgraph_label)
