#  Copyright (c) 2009-2010, Cloud Matrix Pty. Ltd.
#  All rights reserved; available under the terms of the BSD License.

# You'll need a mingw environment set up, plus visual studio, plus activeperl.
# Yes, it's awful.  You're on windows.  Deal with it.

from __future__ import with_statement

import os

from myppy.envs import base

from myppy.recipes import win32 as _win32_recipes


class MyppyEnv(base.MyppyEnv):
    """Myppy environment - win32 version.

    This environment depends on a recent version of MinGW and the associated
    developer tools (which helpfully includes some dependencies such as bz2).
    """

    def __init__(self,rootdir):
        #  Suck in env vars for Visual Studio.
        #  We need these to end up in the actual os.environ dict so
        #  that os.path.expandvars can do its thing.
        #  TODO: get the location of VS dynamically from the environment
        vsdir = "C:\\Program Files\\Microsoft Visual Studio 9.0"
        with open(os.path.join(vsdir,"Common7","Tools","vsvars32.bat")) as f:
            for ln in f:
                ln = ln.strip()
                if ln.lower().startswith("@set "):
                    (_,asgn) = ln.split(None,1)
                    (var,val) = asgn.split("=")
                    val = os.path.expandvars(val)
                    os.environ[var] = val
        super(MyppyEnv,self).__init__(rootdir)
        self._add_env_path("PATH",os.path.join(self.PREFIX,"Python26"))
        self._add_env_path("PATH",os.path.join(self.PREFIX,"Python26","Scripts"))
        self.env = self._fix_env(self.env)

    @property
    def PYTHON_EXECUTABLE(self):
        return os.path.join(self.PREFIX,"Python26","python.exe")

    @property
    def PYTHON_HEADERS(self):
        return os.path.join(self.PREFIX,"Python26","include")

    @property
    def PYTHON_LIBRARY(self):
        return os.path.join(self.PREFIX,"Python26","python26.dll")

    def load_recipe(self,recipe):
        return self._load_recipe_subclass(recipe,MyppyEnv,_win32_recipes)

    def do(self,*cmdline,**kwds):
        kwds.setdefault("shell",True)
        env = kwds.pop("env",None)
        if env is not None:
            env = self._fix_env(env)
        cmdline = self._fix_cmdline(cmdline)
        return super(MyppyEnv,self).do(*cmdline,**kwds)

    def bt(self,*cmdline,**kwds):
        kwds.setdefault("shell",True)
        env = kwds.pop("env",None)
        if env is not None:
            env = self._fix_env(env)
        cmdline = self._fix_cmdline(cmdline)
        return super(MyppyEnv,self).bt(*cmdline,**kwds)

    def _fix_env(self,env):
        for (k,v) in env.iteritems():
            if isinstance(v,unicode):
                env[k] = v = v.encode("utf8")
            if not isinstance(v,str) or not isinstance(k,str):
                raise ValueError("bad env: %r => %r" % (k,v,))
        return env

    def _fix_cmdline(self,cmdline):
        cmdline = list(cmdline)
        if cmdline[0] in ("tar",):
            for i,path in enumerate(cmdline):
                if i == 0:
                    continue
                if len(path) < 3 or not path[1:3] == ":\\":
                    continue
                path = "/" + path.replace(":","").replace("\\","/")
                cmdline[i] = path
        return cmdline

