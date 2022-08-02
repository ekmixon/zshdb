#!/usr/bin/env python
"""We use this to semi-automatically convert command docstrings
to sphinx RsT"""

import sys, os.path, inspect, re
sys.path.insert(0, os.path.abspath('../trepan'))

from trepan.processor.command import mock as Mmock

def camelcase(s):
    return s[0].upper() + s[1:]

def minus2plus(matchobj):
    print("gotone")
    return "\n" + '+' * len(matchobj.group(1)) + "\n"

def cmdDoc2RsT(mod_name):
    exec(f"import trepan.processor.command.{mod_name} as mod")
    classnames = [
        tup[0]
        for tup in inspect.getmembers(mod_name, inspect.isclass)
        if tup[0] != 'DebuggerCommand' and tup[0].endswith('Command')
    ]

    cmd = None
    eval_cmd_template = 'cmd = mod.%s(cp)'
    for classname in classnames:
        eval_cmd = eval_cmd_template % classname
        try:
            exec(eval_cmd)
        except ImportError:
            pass
        except:
            print(f'Error loading {classname} from {mod_name}: {sys.exc_info()[0]}')
    with open(f"commands/{mod_name}.rst", "w") as fdoc:
        ref = f".. _{mod_name}:"
        fdoc.write("%s\n\n" % ref)

        title = f'{camelcase(mod_name)}'
        fdoc.write("%s\n" % title)
        fdoc.write('-' * len(title) + '\n')
        if hasattr(cmd, '__doc__') and cmd.__doc__:
            doc = re.sub(r'\n([-][-]+)\n', minus2plus, cmd.__doc__)
            fdoc.write(doc)
        else:
            print("Can't find __doc__ for %s" % mod_name)
    return


def subCmdDoc2RsT():
    cmd_instances  = []
    eval_cmd_template = 'mod.%s(cp)'
    for mod_name in 'info set show'.split():
        exec(f"import trepan.processor.command.{mod_name} as mod")
        classnames = [
            tup[0]
            for tup in inspect.getmembers(mod_name, inspect.isclass)
            if tup[0] != 'DebuggerCommand' and tup[0].endswith('Command')
        ]

        for classname in classnames:
            eval_cmd = eval_cmd_template % classname
            try:
                instance = eval(eval_cmd)
            except ImportError:
                pass
            except:
                print(f'Error loading {classname} from {mod_name}: {sys.exc_info()[0]}')
        subcmds = instance.cmds.subcmds
        for subname in subcmds:
            with open(f"commands/{mod_name}/{subname}.rst", "w") as fdoc:
                ref = f".. _{mod_name}_{subname}:"
                fdoc.write("%s\n\n" % ref)

                title = f'{camelcase(mod_name)} {camelcase(subname)}'
                fdoc.write("%s\n" % title)
                fdoc.write('-' * len(title) + '\n')
                subcmd = subcmds[subname]
                if hasattr(subcmd, '__doc__') and subcmd.__doc__:
                    doc = re.sub(r'\n([-][-]+)\n', minus2plus, subcmd.__doc__)
                    fdoc.write(doc)
                else:
                    print("Can't find __doc__ for %s" % subname)
    return

d = Mmock.MockDebugger()
d, cp = Mmock.dbg_setup()
cmdDoc2RsT('set')
subCmdDoc2RsT()
