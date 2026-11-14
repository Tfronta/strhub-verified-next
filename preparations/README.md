# Preparations

One file per repository STRhub has prepared by hand. The engine reads these
only when a repository's own instructions were not enough to install and run
the tool as written; then it replays the file and runs the command the
README shows, unchanged.

A preparation says how to get the tool ready: the steps that install or
compile it, the configuration files its README tells the reader to fill in,
and which registered sample (and which layout of its loci) the run reads. It
has **no field for a command, an option or an argument**, and a file with any
other key does not load. See `harness/preparation.py` for the format and
`docs/PREPARATION.md` for the rules.

Every file here is reviewed by the owner before it is merged. Everything in
it is printed in the report of every run that used it.
