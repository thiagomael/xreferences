# X-references &mdash; Cross-References 2 DOT Converter

This script reads a bunch of LaTeX files, maps labels of environments of interest
and then finds out which labels are referenced within these environments, yielding a dependency graph.
The resulting graph is converted to DOT format and wrapped within a `tikzpicture` LaTeX environment.

## Implementation Notes

As a simple, yet reference-package-independent way to search for references, Xreferences uses reference prefixes.
These must be specified in the `reference_prefixes` list.
Environments that should be tracked are specified using the `scope_delimiters` dictionary, which takes the environment's
name as key, and the name inside the closing tag as value.
This is done so that we can, for instance, trace references starting from a theorem's statement (`\begin{theorem}`)
until its proof (`\end{proof}`).
