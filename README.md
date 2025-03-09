# Alpaca - Aleya Linux Package Assistant
This is the official package manager for the Alpaca linux distribution

This package manager is work in progress and will contain bugs. While there are safeguards in place to disable
package installation on any other distribution, please do not try running this script on any other system than
Aleya Linux unless you know what you're doing.

## Installation
Build the package with:

    python -m build

Then install the package with (replace version with the version that was built):

    pip3 install dist/alpaca-version.whl

After that you should generate the default configuration file. This can be done in various ways, but it is recommended as such:

    alpaca dumpconfig > /etc/aleya.conf

## Usage

### Basic flags

To enable verbose output and stack traces you can use the --verbose option in front of any command. For example:

    alpaca --verbose install binutils
    alpaca --verbose update

Do disable seeing the output of code being built (in case there is no binary cache available for a package), you can use the --quit
flag. This reduces the console output significantly as it will only output if there was a problem during the build, but it may be
difficult to see any progress. Note that the --quiet flag can be used in conjunction with --verbose, since quiet only acts on
build output, while verbose acts on the logging of alpaca itself.

    alpaca --quiet install binutils

### Updating repositories

To update your local repository cache to see if there are new versions or new packages available, you can use

    alpaca update

### Package installation

Packages can be installed using the install command. If no version was specified, the latest version of the package will be installed:

    alpaca install binutils

You can also specify explicitly that you want to use the latest version; but not specifying any version will achieve the same. The
following command is the same as above:

    alpaca install binutils/latest

You can install a specific version by specifying it (assuming it is available as a version in any of you chosen package repositories:

    alpaca install binutils/2.44-1

If a prebuilt binary is available, this will be used. If it is not, Alpaca will try to build the package from source.
You can enforce building from source by providing the --build flag

    alpaca install --build binutils

Alpaca will always try to clean up after a build, regardless if an error happened or not. This is to prevent the system from clogging
up with random source files and build artifacts. For troubleshooting purposes it might be needed to keep these files in case of a failure.
For this you can specify the --keep flag. In case of a build failure, all sources and intermediate build results are kept. If the package
is installed successfully, the files will be deleted regardless.

    alpaca install --build --keep binutils

You can choose to install packages into a different directory than the system root ('/'). This is typically used when performing a new
installation to a disk. You can use the --target PATH flag to achieve this.

    alpaca install --target /mnt/aleya binutils

Note that due to technical limitations, the post-build hooks will not be ran for these packages. You must do so manually after
entering the newly installed system in a chroot, by using the following command:

    alpaca upgrade --post

### Cache cleanup

Under normal conditions Alpaca tries to always clean up after itself. In case you wish to clean up the Alpaca build cache anyway,
you can use the prune command. This will not delete your local prebuilt binaries.

    alpaca prune

If you also wish to clean up your locally built binary cache, you can use the -a flag.

    alpaca prune -a
