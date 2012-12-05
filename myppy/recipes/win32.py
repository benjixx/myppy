#  Copyright (c) 2009-2010, Cloud Matrix Pty. Ltd.
#  All rights reserved; available under the terms of the BSD License.

from __future__ import with_statement

import os
import sys
import tempfile
import stat
import urlparse
import urllib2
import subprocess
import shutil
from textwrap import dedent

from myppy.util import md5file, do, bt, cd, relpath, tempdir, chstdin

from myppy.recipes import base

class Recipe(base.Recipe):

    @property
    def INSTALL_PREFIX(self):
        prefix = super(Recipe,self).INSTALL_PREFIX
        drive,path = os.path.splitdrive(prefix)
        return "/" + drive[0] + path.replace("\\","/")
        
    def _generic_configure(self,script=None,vars=None,args=None,env={}):
        if script is None:
            script = self.CONFIGURE_SCRIPT
        script = ["sh","-C",script]
        super(Recipe,self)._generic_configure(script,vars,args,env)


class lib_zlib(base.lib_zlib,Recipe):
    def _configure(self):
        pass
    def _patch(self):
        def add_env_vars(lines):
            for ln in lines:
                if ln.startswith("SHARED_MODE ="):
                    ln = "SHARED_MODE=1\n"
                yield ln
                if ln.startswith("PREFIX ="):
                    yield "INCLUDE_PATH = " + self.INSTALL_PREFIX + "\\include\n"
                    yield "LIBRARY_PATH = " + self.INSTALL_PREFIX + "\\lib\n"
        self._patch_build_file("win32/Makefile.gcc",add_env_vars)
    def _make(self):
        self._generic_make(makefile="win32/Makefile.gcc")
    def install(self):
        self._generic_make(target="install",makefile="win32/Makefile.gcc")


#  We must build bz2 with Visual Studio so python can link to it.
class lib_bz2(base.lib_bz2,Recipe):
    def _make(self):
        workdir = self._get_builddir()
        with cd(workdir):
            self.target.do("nmake","-f","makefile.msc")
    def install(self):
        workdir = self._get_builddir()
        shutil.copyfile(os.path.join(workdir,"libbz2.lib"),
                        os.path.join(self.PREFIX,"lib","libbz2.lib"))
        shutil.copyfile(os.path.join(workdir,"bzlib.h"),
                        os.path.join(self.PREFIX,"include","bzlib.h"))


class lib_sqlite3(base.lib_sqlite3,Recipe):
    def install(self):
        super(lib_sqlite3,self).install()
        workdir = self._get_builddir()
        shutil.copyfile(os.path.join(workdir,"sqlite3.c"),
                        os.path.join(self.PREFIX,"include","sqlite3.c"))

#  Python is a very special case, as it's just not possible to build it
#  using anything other than Visual Studio.  So, we slog through...
class python26(base.python26,Recipe):
    def _patch(self):
        super(python26,self)._patch()
        workdir = self._get_builddir()
        #  Munge build script to find bz2
        def set_bz2_paths(lines):
            for ln in lines:
                if "$(bz2Dir)" in ln:
                    if "AdditionalIncludeDirectories" in ln:
                        ln = ln.replace("$(bz2Dir)",
                                        os.path.join(self.PREFIX,"include"))
                    elif "AdditionalDependencies" in ln:
                        ln = "AdditionalDependencies=\"%s\"\n"
                        ln %= (os.path.join(self.PREFIX,"lib","libbz2.lib"),)
                    elif ln.strip().startswith("CommandLine"):
                        ln = "CommandLine=\"true\"\n"
                yield ln
        self._patch_build_file("PCbuild\\bz2.vcproj",set_bz2_paths)
        #  Munge build script to find sqlite3
        def set_sqlite3_paths(lines):
            for ln in lines:
                if "$(sqlite3Dir)" in ln:
                    ln = ln.replace("&quot;","")
                    ln = ln.replace("$(sqlite3Dir)",
                                    os.path.join(self.PREFIX,"include"))
                yield ln
        self._patch_build_file("PCbuild\\_sqlite3.vcproj",set_sqlite3_paths)
        self._patch_build_file("PCbuild\\sqlite3.vcproj",set_sqlite3_paths)
        self._patch_build_file("PCbuild\\sqlite3.vsprops",set_sqlite3_paths)
        shutil.copyfile(os.path.join(self.PREFIX,"lib","libsqlite3.a"),
                        os.path.join(workdir,"PCbuild","libsqlite3.lib"))
    def _configure(self):
        # don't call ./configure
        self._post_config_patch()
    def _make(self):
        workdir = self._get_builddir()
        workdir = os.path.join(workdir,"PCbuild")
        with cd(workdir):
            #  This will fail when it can't find bsddb, tk, etc
            try:
                self.target.do("build.bat")
            except subprocess.CalledProcessError:
                if not os.path.exists(os.path.join(workdir,"python.exe")):
                    raise
    def _add_builtin_module(self,modnm):
        #  Actually, they're all already builtin on windows
        pass
    def install(self):
        workdir = self._get_builddir()
        insdir = os.path.join(self.target.PREFIX,"Python26")
        if not os.path.isdir(insdir):
            os.makedirs(insdir)
        shutil.copyfile(os.path.join(workdir,"PCbuild","python.exe"),
                        os.path.join(insdir,"python.exe"))
        shutil.copyfile(os.path.join(workdir,"PCbuild","pythonw.exe"),
                        os.path.join(insdir,"pythonw.exe"))
        shutil.copyfile(os.path.join(workdir,"PCbuild","python26.dll"),
                        os.path.join(insdir,"python26.dll"))
        shutil.copytree(os.path.join(workdir,"Lib"),
                        os.path.join(insdir,"Lib"))
        shutil.copytree(os.path.join(workdir,"Include"),
                        os.path.join(insdir,"include"))
        pyddir = os.path.join(insdir,"DLLs")
        if not os.path.isdir(pyddir):
            os.makedirs(pyddir)
        for nm in os.listdir(os.path.join(workdir,"PCbuild")):
            if nm.endswith(".pyd"):
                shutil.copyfile(os.path.join(workdir,"PCbuild",nm),
                                os.path.join(pyddir,nm))

