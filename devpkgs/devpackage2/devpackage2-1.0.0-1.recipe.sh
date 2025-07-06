# Maintainer: Robin 'Ruadeil' Degen <mail@ruadeil.lgbt>
# This is a development test package. This means it is harmless to install
# it on a working system, for testing purposes.

name="devpackage2"
version="1.0.0"
release="1"
url="https://ruadeil.lgbt"
licenses=('GPLv3')
dependencies=()
build_dependencies=()
sources=()
sha256sums=()

handle_package() {
    mkdir -p $package_directory/devpkgs/devpackage2
    touch $package_directory/devpkgs/testfile1.txt
    touch $package_directory/devpkgs/testfile2.txt

    cd hebaselfjkrkj
    mkdir /test
}
