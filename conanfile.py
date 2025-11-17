from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import check_min_cppstd
from conan.tools.files import (
    apply_conandata_patches, copy, export_conandata_patches,
    get, rm, rmdir, replace_in_file
    )
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.microsoft import is_msvc
from conan.tools.system.package_manager import Apt
import os

required_conan_version = ">=2.0"


class PackageConan(ConanFile):
    name = "spral"
    description = "Sparse Parallel Robust Algorithms Library"
    license = "BSD-3-Clause"
    url = "https://github.com/sintef-ocean/conan-spral"
    homepage = "https://ralna.github.io/spral/"
    topics = ("linear-algebra")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_openmp": [True, False],
        "with_64bit_int": [True, False]
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_openmp": True,
        "with_64bit_int": False

    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

        self.options["metis"].with_64bit_types = self.options.with_64bit_int

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # Prefer self.requirements() method instead of self.requires attribute.
        self.requires("metis/5.2.1")
        self.requires("openblas/0.3.30")
        self.requires("hwloc/2.11.1")
        if self.options.with_openmp:
            if not self.settings.os == "Windows":
                if not self.settings.compiler == "gcc":
                    self.requires("llvm-openmp/20.1.6")

    def validate(self):
        check_min_cppstd(self, 11)
        #if is_msvc(self) and self.info.options.shared:
        #    raise ConanInvalidConfiguration(f"{self.ref} can not be built as shared on Visual Studio and msvc.")

    def build_requirements(self):
        self.tool_requires("meson/[>=1.2.3 <2]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        rep_libs = [("hwloc", "false"), ("metis", "true")]
        for lib in rep_libs:
            replace_in_file(self,
                            os.path.join(self.source_folder, "meson.build"),
                            f"lib{lib[0]} = fc.find_library(lib{lib[0]}_name, dirs : lib{lib[0]}_path, required : {lib[1]})",
                            f"lib{lib[0]} = dependency(lib{lib[0]}_name, required : true)")

    def generate(self):
        def feature(v): return "enabled" if v else "disabled"

        deps = PkgConfigDeps(self)
        deps.generate()

        tc = MesonToolchain(self)
        tc.project_options["modules"] = True
        tc.project_options["examples"] = False
        tc.project_options["tests"] = False
        tc.project_options["gpu"] = False  # Requires CCI's hwloc to support it too
        tc.project_options["metis64"] = self.options.with_64bit_int
        tc.project_options["openmp"] = self.options.with_openmp

        tc.project_options["libmetis_version"] = "5"
        tc.project_options["libblas"] = "openblas"
        tc.project_options["liblapack"] = "openblas"
        tc.project_options["libhwloc"] = "hwloc"
        tc.project_options["libmetis"] = "metis"

        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()

        rm(self, "*.pdb", self.package_folder, recursive=True)
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.libs = ["spral"]
        self.cpp_info.set_property("pkg_config_name", "spral")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["m", "mvec", "udev"])
            self.cpp_info.system_libs.extend(["gfortran", "quadmath"])
        self.cpp_info.requires.extend(["openblas::openblas", "metis::metis", "hwloc::hwloc"])

        if self.options.with_openmp:
            if self.settings.compiler == "gcc":
                self.cpp_info.system_libs.extend(["gomp"])
            elif not self.settings.os == "Windows":
                self.cpp_info.requires.append("llvm-openmp::llvm-openmp")

    def system_requirements(self):
        if self.settings.compiler == "gcc":
            # Depends on gcc version..
            Apt(self).install(["libgfortran5", "libquadmath0"])
            if self.options.with_openmp:
                Apt(self).install(["libgomp1"])
