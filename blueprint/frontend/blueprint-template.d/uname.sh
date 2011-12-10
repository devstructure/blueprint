# uname(1) properties for use in Blueprint file templates.

# The kernel name.  This is always "Linux" on systems Blueprint supports.
export KERNEL="$(uname -s)"

# The kernel release.
export KERNEL_RELEASE="$(uname -r)"

# The system's hardware architecture.  Probably "i386" or "x86_64".
export ARCH="$(uname -i)"
