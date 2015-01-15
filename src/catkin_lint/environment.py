#!/usr/bin/env python
"""
Copyright (c) 2013-2015 Fraunhofer FKIE

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

 * Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
 * Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
 * Neither the name of the Fraunhofer organization nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
import os
import sys
from .packages import find_packages
from .util import iteritems


class CatkinEnvironment(object):
    def __init__(self, rosdep_view=None):
        self.manifests = {}
        self.known_catkin_pkgs = set([])
        self.known_other_pkgs = set([])
        if rosdep_view is None:
            try:
                from rosdep2.lookup import RosdepLookup
                from rosdep2.rospkg_loader import DEFAULT_VIEW_KEY
                from rosdep2.sources_list import SourcesListLoader
                sources_loader = SourcesListLoader.create_default()
                lookup = RosdepLookup.create_from_rospkg(sources_loader=sources_loader)
                self.rosdep_view = lookup.get_rosdep_view(DEFAULT_VIEW_KEY)
            except Exception as err:
                sys.stderr.write("catkin_lint: cannot load rosdep database: %s\n" % str(err))
                sys.stderr.write("catkin_lint: unknown dependencies will be ignored\n")
                self.rosdep_view = {}
        else:
            self.rosdep_view = rosdep_view
        self.cache = {}

    def add_path(self, path):
        if not os.path.isdir(path):
            return []
        realpath = os.path.realpath(path)
        if realpath in self.cache:
            return self.cache[realpath]
        pkgs = find_packages(path)
        found = []
        for p, m in iteritems(pkgs):
            is_catkin = True
            for e in m.exports:
                if e.tagname == "build_type" and e.content != "catkin":
                    is_catkin = False
                    break
            if is_catkin:
                self.known_catkin_pkgs.add(m.name)
                pm = ( os.path.join(path, p), m )
                self.manifests[m.name] = pm
                found.append(pm)
            else:
                self.known_other_pkgs.add(m.name)
        self.cache[realpath] = found
        return found

    def is_catkin_pkg(self, name):
        if name in self.known_catkin_pkgs: return True
        if name in self.known_other_pkgs: return False
        try:
            # FIXME _is_ros is also true for build_type != catkin
            return self.rosdep_view.lookup(name).data["_is_ros"]
        except (KeyError, AttributeError):
            return False

    def is_system_pkg(self, name):
        if name in self.known_other_pkgs: return True
        if name in self.known_catkin_pkgs: return False
        if name in self.ros_dep_view.keys():
            try:
                # FIXME _is_ros is also true for build_type != catkin
                return not self.rosdep_view.lookup(name).data["_is_ros"]
            except (KeyError, AttributeError):
                return True
        return False

    def is_known_pkg(self, name):
        return name in self.rosdep_view.keys() or name in self.known_catkin_pkgs or name in self.known_other_pkgs

    def has_rosdep(self):
        return len(self.rosdep_view.keys()) > 0

    def disable_rosdep(self):
        self.rosdep_view = {}
