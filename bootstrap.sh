echo "Paste the contents of ~/production.pem here and press ^D:" >&2
cat >"$HOME/production.pem"
chmod 600 "$HOME/production.pem"

apt-get -q update

apt-get -q -y install \
	build-essential \
	git-core \
	python python-setuptools \
	ruby ruby-dev rubygems \

gem install fpm

mkdir "$HOME/work"
cd "$HOME/work"
git clone git://github.com/devstructure/blueprint.git
(cd "blueprint" && git submodule update --init)
git clone git://github.com/rcrowley/ronn.git -b dots
