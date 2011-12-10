# LSB properties for use in Blueprint file templates.

# The distro name.
export DISTRO="$(lsb_release -si 2>/dev/null || {
	if [ -f "/etc/debian_version" ]
	then echo "Debian"
	elif [ -f "/etc/fedora-release" ]
	then echo "Fedora"
	elif [ -f "/etc/redhat-release" ]
	then
		if grep -i "CentOS" "/etc/redhat-release"
		then echo "CentOS"
		elif grep -i "Scientific" "/etc/redhat-release"
		then echo "Scientific"
		else echo "RedHat"
		fi
	fi
})"

# The operating system release codename.
export RELEASE="$(lsb_release -sc 2>/dev/null || {
	if [ -f "/etc/debian_version" ]
	then cat "/etc/debian_version"
	elif [ -f "/etc/redhat-release" ]
	then egrep -o "release [0-9.]+" /etc/redhat-release | cut -d" " -f2
	fi
})"
