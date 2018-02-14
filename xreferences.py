#!/usr/bin/env python
#coding=utf-8
"""
Script to extract cross-references in a LaTeX document.
"""

from dependency_graph import *

from collections import namedtuple

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


def parse_scope_or_restatement(line, dependency_graph):
    # If we find a restatement, we need to search for further dependencies
    for macro, restatable in _get_restatables():
        if (r'\%s' % macro ) in line:
            log(u"Re-opening restatable "+restatable.label)
            return lambda l, dg: parse_scope_end(l, dg, restatable.type, restatable.label)
    # Otherwise, we treat the line as a possible scope beginning
    return parse_scope_begin(line, dependency_graph)


def parse_scope_begin(line, dependency_graph):
    scope_type = _parse_scope_type(line)
    if scope_type is not None:
        scope_description = _parse_scope_description(line)
        log(u"Beginning scope " + scope_type + unicode(scope_description))
        if scope_type == "restatable":
            _prepare_restatable(_parse_restatable_type(line), _parse_restatable_macro(line))
        return lambda l, dg: parse_scope_label(l, dg, scope_type, scope_description)
    return None


def parse_scope_label(line, dependency_graph, scope_type, scope_description):
    label = _parse_scope_label(line)
    if label is None:
        raise Exception("A scope must always be followed by a label")
    log("Scope label: " + label)
    dependency_graph.add_custom_name(label, scope_description)
    if scope_type == "restatable":
        _record_restatable(label)
    return lambda l, dg: parse_scope_end(l, dg, scope_type, label)


def parse_scope_end(line, dependency_graph, scope_type, label):
    if _is_scope_end(line, scope_type):
        log("Ending scope %s (%s)" % (label, scope_type))
        return default_parser

    references = _parse_references(line, list())
    for reference in references:
        log(u"%s depends on %s" % (label, reference))
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
        # Let us get rid of occurrences that are just regular sentences
        # ending with a colon (e.g., "the following property:")
        if not reference.endswith(':'):
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


default_parser = parse_scope_or_restatement


############################
# Restatable-specific code
############################

_tmp_restatement_type = None
_tmp_restatement_macro = None

# Tuple for properties of restatable theorems
Restatable = namedtuple("Restatable", ["label", "type"])

# Mapping of restatement macros to corresponding restatable properties
restatables = dict()


def _prepare_restatable(restatement_type, restatement_macro):
    global _tmp_restatement_type
    global _tmp_restatement_macro
    _tmp_restatement_type = restatement_type
    _tmp_restatement_macro = restatement_macro


def _record_restatable(restatement_label):
    global _tmp_restatement_type
    global _tmp_restatement_macro
    restatables[_tmp_restatement_macro] = Restatable(restatement_label, _tmp_restatement_type)
    _tmp_restatement_type = None
    _tmp_restatement_macro = None


def _get_restatables():
    return restatables.iteritems()


def _parse_restatable_type(line):
    last_bracket = line.find(']')
    return _parse_brace_content(line[last_bracket:])


def _parse_restatable_macro(line):
    last_opening_brace = line.rfind('{')
    return _parse_brace_content(line[last_opening_brace:])

############################
# Presentation-specific code
############################

def dump(graph_dot, label):
    tikz_output = r"""
\begin{tikzpicture}[
        align=center,
        text centered,
        text width=80pt]
    \fontsize{9}{10.8}
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
    parser = argparse.ArgumentParser(description="Parse LaTeX files and track cross-references.")
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

    if len(configs.tex_files) == 0:
        exit()
    # Concatenate files as if they were a single one
    dg = parse_tex(fileinput.input(configs.tex_files,
                                   openhook=fileinput.hook_encoded("utf-8")))
    if args.output == 'dot':
        dump(dg.to_dot(label_colorizer), "theory-structure")
        dump(dg.filtered(["def:", "property:", "strategy:"]).to_dot(label_colorizer), "theory-structure-definitions")
        dump(dg.filtered(["theorem:", "lemma:", "corollary:"]).to_dot(label_colorizer), "theory-structure-theorems")
        for subgraph_label in configs.subgraphs:
            dump(dg.subgraph(subgraph_label).to_dot(label_colorizer), subgraph_label)
    elif args.output == 'table':
        for reference, table_file_conf in configs.table_files.iteritems():
            with codecs.open(table_file_conf['name'], 'w', encoding="utf-8") as out:
                out.write(dg.to_tabular_rows(reference, add_references=table_file_conf['add_references']))
