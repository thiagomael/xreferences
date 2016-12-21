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
        self._node_bodies = defaultdict(str)
        self._order = list()

    def add_dependency(self, dependent, dependency):
        if dependent != dependency: # Avoid cycles
            self._adjacencies[dependent].add(dependency)
            self._nodes.add(dependent)
            self._nodes.add(dependency)

    def add_content(self, node_label, content):
        self._node_bodies[node_label] += content
        if node_label not in self._order:
            self._order.append(node_label)

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

    def to_dot(self, label_processor=lambda _,x:x):
        nodes = {node: "n"+str(i) for i, node in enumerate(self._nodes)}
        nodes_declaration = ['%s [texlbl="%s"];' % (id_, self._make_dot_label(node, label_processor)) for node, id_ in nodes.iteritems()]

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

    def to_tabular_rows(self, prefix, add_references):
        node_labels = filter(lambda label: label.startswith(prefix),
                             self._order)
        rows = []
        for label in node_labels:
            this = self._make_references([label])
            body = self._node_bodies[label]
            row = this + " & " + body
            if add_references:
                references = self._make_references(self._adjacencies[label])
                row += " & " + references
            rows.append(row + r" \\")
        return "\n\hline\n".join(rows)

    def _make_references(self, adjacencies):
        return r"\Cref{%s}" % ",".join(adjacencies)

    def _visit(self, label):
        nodes = set([label])
        adjacencies = self._adjacencies[label]
        for adjacency in adjacencies:
            nodes.update(self._visit(adjacency))
        return nodes

    def _make_dot_label(self, node_tex_label, label_processor):
        custom_label = self._node_names.get(node_tex_label)
        if custom_label is not None:
            processed = label_processor(node_tex_label, custom_label)
            return r"\hyperref[%s]{%s}" % (node_tex_label, processed)
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
    dependency_graph.add_content(label, line)
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


def _make_label_colorizer(colors_by_prefixes):
    def label_colorizer(node_ref, label):
        for prefix in colors_by_prefixes:
            if node_ref.startswith(prefix):
                return r"\textcolor{%s}{%s}" % (colors_by_prefixes[prefix], label)
        return label
    return label_colorizer


# Configuration
# We search from \begin{<key>} until \end{<value>}.
scope_delimiters = None
reference_prefixes = None
#------------------------------------------------

from collections import namedtuple
import json

Configuration = namedtuple('Configuration',
                           ['scope_delimiters',
                            'reference_prefixes',
                            'colors_by_prefixes',
                            'tex_files',
                            'subgraphs',
                            'table_files'])

def _parse_configuration(config_file):
    global scope_delimiters
    global reference_prefixes

    raw_config = json.load(config_file)

    scope_delimiters = raw_config['scope_delimiters']
    reference_prefixes = raw_config['reference_prefixes']
    return Configuration(scope_delimiters=scope_delimiters,
                         reference_prefixes=reference_prefixes,
                         colors_by_prefixes=raw_config['colors_by_prefixes'],
                         tex_files=raw_config['tex_files'],
                         subgraphs=raw_config['subgraphs'],
                         table_files=raw_config['table_files'])

import argparse
import fileinput
import codecs

def _parse_args():
    '''
    Parses command-line args.
    Return object:
        - output: dot|table.
        - config: configuration file object.
    '''
    parser = argparse.ArgumentParser(description="Run ReAna's strategies for a number of SPLs.")
    parser.add_argument('--output',
                        dest='output',
                        action='store',
                        required=True,
			choices=['dot', 'table'],
                        help="Output mode: do you want to generate DOT files or LaTeX tables?")
    parser.add_argument('--config',
                        dest='config_file',
                        action='store',
                        required=True,
                        type=file,
                        help="Configuration file.")
    return parser.parse_args()

if __name__ == '__main__':
    args = _parse_args()
    configs = _parse_configuration(args.config_file)

    label_colorizer = _make_label_colorizer(configs.colors_by_prefixes)

    # Concatenate files as if they were a single one
    dg = parse_tex(fileinput.input(configs.tex_files,
                                   openhook=fileinput.hook_encoded("utf-8")))
    if args.output == 'dot':
        dump(dg.to_dot(label_colorizer), "theory-structure")
        for subgraph_label in configs.subgraphs:
            dump(dg.subgraph(subgraph_label).to_dot(label_colorizer), subgraph_label)
    elif args.output == 'table':
        for reference, table_file_conf in configs.table_files.iteritems():
            with codecs.open(table_file_conf['name'], 'w', encoding="utf-8") as out:
                out.write(dg.to_tabular_rows(reference, add_references=table_file_conf['add_references']))
