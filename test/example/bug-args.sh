#!/usr/bin/zsh
echo Dollar 0 is $(basename $0)
echo First parm is: $1
set a b c d e
shift 2
# At this point we shouldn't have a $5 or a $4
0="foo"
echo Dollar 0 is now $0
exit 0
