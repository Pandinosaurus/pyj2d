#Copyright (c) 2011 - MIT License

import os, sys


if os.name != 'java':
    print('Use Jython to run script')
    sys.exit()


jframe = None

japplet = None

event = None

