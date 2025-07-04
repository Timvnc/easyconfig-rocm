# -*- coding: utf-8 -*-
##
# Copyright 2009-2025 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# https://github.com/easybuilders/easybuild
#
# EasyBuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
#
# EasyBuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EasyBuild.  If not, see <http://www.gnu.org/licenses/>.
##
"""
EasyBuild support for building and installing ROCm-LLVM, AMD's fork of the LLVM compiler infrastructure.

@author: Bob Dröge (University of Groningen)
"""
import os

from easybuild.tools import LooseVersion
from easybuild.easyblocks.llvm import EB_LLVMtest, general_opts
from easybuild.tools.filetools import apply_regex_substitutions, mkdir, remove_dir

class EB_ROCm_minus_LLVM(EB_LLVMtest):
    """
    Support for building the ROCm-LLVM compilers with some modifications on top of the LLVM easyblock.
    """

    def _configure_general_build(self):
        super(EB_ROCm_minus_LLVM, self)._configure_general_build()
        self._cmakeopts.update({
            'LLVM_EXTERNAL_PROJECTS': '"device-libs"',
            'LLVM_EXTERNAL_DEVICE_LIBS_SOURCE_DIR': os.path.join(self.llvm_src_dir, 'amd', 'device-libs '),
            'LLVM_ENABLE_PER_TARGET_RUNTIME_DIR': 'ON',
            'CLANG_DEFAULT_RTLIB': 'compiler-rt',
            'CLANG_DEFAULT_UNWINDLIB': 'libgcc',
            'DEFAULT_ROCM_PATH': self.installdir,
        })


        if LooseVersion('19') <= LooseVersion(self.version) < LooseVersion('20'):
            self.runtimes_cmake_args['LIBOMPTARGET_AMDGCN_GFXLIST'] = '%s' % '|'.join(self.amd_gfx)
        self.runtimes_cmake_args['AMDDeviceLibs_DIR'] = os.path.join(
            self.llvm_obj_dir_stage2, 'tools', 'device-libs', 'lib64', 'cmake', 'AMDDeviceLibs'
        )
        self._add_cmake_runtime_args()

    def configure_step(self):
        # the openmp component uses the same build dirs, so we need to remove them to make sure that we start with clean ones
        if os.path.exists(os.path.join(self.builddir, 'llvm.obj.1', 'CMakeCache.txt')):
            remove_dir(os.path.join(self.builddir, 'llvm.obj.1'))
            remove_dir(os.path.join(self.builddir, 'llvm.obj.2'))
            remove_dir(os.path.join(self.builddir, 'llvm.obj.3'))
        super(EB_ROCm_minus_LLVM, self).configure_step()

        if 'openmp' in self.final_projects:
            # fix path to include dir for omp.h:
            omp_header_regex = [(r'\${CMAKE_BINARY_DIR}/projects/openmp/runtime/src', '${CMAKE_BINARY_DIR}/../../projects/openmp/runtime/src')]
            apply_regex_substitutions(os.path.join(self.llvm_src_dir, 'offload',  'DeviceRTL', 'CMakeLists.txt'), omp_header_regex)

        # no hardcoded path to clang to make sure it picks up the right ones (which can be the RPATH wrappers)
        amdllvm_cmakelists = os.path.join(self.llvm_src_dir, 'clang-tools-extra', 'amdllvm', 'CMakeLists.txt')
        apply_regex_substitutions(amdllvm_cmakelists, [(r'set\(CMAKE_CXX_COMPILER', '# set(CMAKE_CXX_COMPILER')])

    def _configure_final_build(self):
        super(EB_ROCm_minus_LLVM, self)._configure_final_build()
        self._cmakeopts.update({
            'LIBOMP_OMPD_SUPPORT': 'ON',
            'CLANG_ENABLE_AMDCLANG': 'ON',
            #'LIBOMPTARGET_FORCE_DLOPEN_LIBHSA': 'ON', # doesn't seem to work
        })
        self._configure_general_build()

