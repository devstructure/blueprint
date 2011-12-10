# Network properties for use in Blueprint file templates.

# Each IPv4 address assigned to an interface, one per line.
export EACH_IP="$(ifconfig | egrep -o "inet addr:[0-9.]+" | cut -d":" -f2)"

# Each IPv6 address assigned to an interface, one per line.
export EACH_IPv6="$(ifconfig | egrep -o "inet6 addr: [0-9a-f:/]+" | cut -d" " -f3)"

# The first IPv6 address assigned to any interface.
export IPv6="$(echo "$EACH_IPv6" | head -n1)"

# The first private IPv4 address assigned to any interface.
export PRIVATE_IP="$(echo "$EACH_IP" | while read IP
do
	case "$IP" in
		"10."*) echo "$IP";;
		"127."*) ;;
		"172.16."*|"172.32."*|"172.48."*|"172.64."*|"172.80."*|"172.96."*|"172.112."*|"172.128."*|"172.144."*|"172.160."*|"172.176."*|"172.192."*|"172.208."*|"172.224."*|"172.240."*) echo "$IP";;
		"192.168."*) echo "$IP";;
		*) ;;
	esac
done | head -n1)"

# The first public IPv4 address assigned to any interface.
export PUBLIC_IP="$(echo "$EACH_IP" | while read IP
do
	case "$IP" in
		"10."*) ;;
		"127."*) ;;
		"172.16."*|"172.32."*|"172.48."*|"172.64."*|"172.80."*|"172.96."*|"172.112."*|"172.128."*|"172.144."*|"172.160."*|"172.176."*|"172.192."*|"172.208."*|"172.224."*|"172.240."*) ;;
		"192.168."*) ;;
		*) echo "$IP";;
	esac
done | head -n1)"

export HOSTNAME="$(hostname)"

export DNSDOMAINNAME="$(dnsdomainname)"

export FQDN="$(hostname --fqdn)"
