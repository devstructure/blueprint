if [ ! -f "$HOME/production.pem" ]
then
	echo "Paste the contents of ~/production.pem here and press ^D:" >&2
	cat >"$HOME/production.pem"
	chmod 600 "$HOME/production.pem"
fi

sudo apt-get -q update

sudo apt-get -q -y install \
	"build-essential" \
	"git-core" \
	"python" "python-dev" "python-pip" "python-setuptools" \
	"ruby" "ruby-dev" "rubygems" \

sudo gem install --no-rdoc --no-ri "fpm"

sudo pip install boto flask gunicorn nose nose_cov

mkdir -p "$HOME/work"
cd "$HOME/work"
[ -d "blueprint" ] || git clone "git://github.com/devstructure/blueprint.git"
(cd "blueprint" && git submodule update --init)
[ -d "ronn" ] || git clone "git://github.com/rcrowley/ronn.git" -b "dots"
