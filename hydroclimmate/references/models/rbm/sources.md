# RBM sources and identity limits

Checked: 2026-09-16. Candidate: UW-Hydro/RBM master (floating, no commit pinned). Lab implementation: unconfirmed. No RBM build, input conversion or run was performed.

## R1

[Model overview](https://github.com/UW-Hydro/RBM/blob/master/docs/Overview/ModelOverview.md): raw file retrieved; one-dimensional thermal model, semi-Lagrangian method and model lineage.

## R2

[VIC-RBM tutorial](https://github.com/UW-Hydro/RBM/blob/master/docs/Documentation/tutorial.md): raw file retrieved; component roles, input categories and output classes. Contains legacy VIC discussion; do not interpret it as VIC5 documentation. This is a workflow example, not an identity check for the lab's model.

## R3

[Salmon River run guide](https://github.com/UW-Hydro/RBM/blob/master/docs/Documentation/run_RBM.md): raw file retrieved; explicitly VIC_RBM2.2/VIC4.2.d, topology and Appendix A input/output descriptions. The guide contains daily assumptions and internal inconsistencies, including executable naming; no command, full unit table or parser is adopted. The broad tutorial's subdaily statement must not override this example's narrower scope.

## R4

[UW-Hydro repository README](https://github.com/UW-Hydro/RBM): retrieved; repository identity, research-software limitations, references and documentation links.

## Retrieval and coverage gaps

The repository-linked Read the Docs endpoint could not be fetched in the web tool during research; raw GitHub documentation above was retrieved instead. The repository's mkdocs configuration also references a different fork/site, so documentation branding alone is not sufficient to identify a code lineage.

Reservoir extensions, DHSVM coupling recipes, exact restart behavior and current lab formats are not covered. EPA RBM10 and other forks must not be silently substituted. Upstream documentation/license remains upstream; these files contain original summaries and explicit analysis recommendations rather than redistributed source or manuals.
