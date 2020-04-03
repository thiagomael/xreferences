#coding=utf-8
"""
Dependency graphs
"""

from collections import defaultdict
from itertools import chain, product


class DependencyGraph(object):
    def __init__(self):
        self._adjacencies = defaultdict(set)
        self._nodes = set()
        self._node_names = dict()
        self._node_bodies = defaultdict(unicode)
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

    def filtered(self, label_prefixes):
        """
        Returns a new DependencyGraph without nodes unreachable from
        the one whose label is passed as an argument.
        """
        nodes = [node for node in self._nodes if any(node.startswith(prefix) for prefix in label_prefixes)]
        new_graph = DependencyGraph()
        new_graph._adjacencies.update({node: self._adjacencies[node] for node in nodes})
        new_graph._nodes.update(nodes)
        new_graph._node_names = {label: name for label, name in self._node_names.iteritems() if label in nodes}
        return new_graph

    def to_dot(self, label_processor=lambda _,x:x, plain_labels=False):
        nodes = {node: "n"+str(i) for i, node in enumerate(self._nodes)}
        if plain_labels:
            nodes_declaration = ['%s;' % (id_) for node, id_ in nodes.iteritems()]
        else:
            nodes_declaration = ['%s [texlbl="%s"];' % (id_, self._make_dot_label(node, label_processor)) for node, id_ in nodes.iteritems()]

        exploded_dependencies = chain(*[product([dependent], dependencies) for dependent, dependencies in self._adjacencies.iteritems()])
        edges = ['%s -> %s;' % (nodes[dependent], nodes[dependency]) for dependent, dependency in exploded_dependencies if dependency in nodes]

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

    def dump_labels_as_table_rows(self):
        labels = self._order
        for label in labels:
            print r"""\fullref{%s}
& \repolink{}{}{}
\\""" % label
