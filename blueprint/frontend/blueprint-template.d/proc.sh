# System properties from `/proc` for use in Blueprint file templates.

# The number of cores in the system.  The semantics of this value when read
# in a virtualized environment are undefined.
export CORES="$(grep "^processor" "/proc/cpuinfo" | wc -l)"

# The total amount of memory in the system in bytes.
export MEM="$(grep "^MemTotal" "/proc/meminfo" | awk '{print $2 * 1024}')"
