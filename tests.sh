BASE="http://127.0.0.1:5000"
CURLARGS="-sv"

SECRET="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_-"
NAME="test"
SHA="adff242fbc01ba3753abf8c3f9b45eeedec23ec6"

set -ex

cd "$(dirname "$0")"

curl $CURLARGS -X GET "$BASE/secret"

curl $CURLARGS -X PUT \
	-H "Content-Type: application/json" \
	-T "tests/empty.json" "$BASE/invalid/$NAME"

curl $CURLARGS -X PUT \
	-H "Content-Type: application/json" \
	-T "tests/empty.json" "$BASE/$SECRET/%20"

curl $CURLARGS -X PUT \
	-H "Content-Type: application/json" \
	-T "tests/invalid-syntax.json" "$BASE/$SECRET/$NAME"

curl $CURLARGS -X PUT \
	-H "Content-Type: application/json" \
	-T "tests/invalid-schema.json" "$BASE/$SECRET/$NAME"

curl $CURLARGS -X PUT \
	-H "Content-Type: application/json" \
	-T "tests/empty.json" "$BASE/$SECRET/$NAME"
curl $CURLARGS -X PUT \
	-H "Content-Type: application/x-tar" \
	-T "tests/$SHA.tar" "$BASE/$SECRET/$NAME/$SHA.tar"

curl $CURLARGS -X PUT \
	-H "Content-Type: application/json" \
	-T "tests/sources.json" "$BASE/$SECRET/$NAME"
curl $CURLARGS -X PUT \
	-H "Content-Type: application/x-tar" \
	-T "tests/$SHA.tar" "$BASE/$SECRET/$NAME/$SHA.tar"

curl $CURLARGS -X PUT \
	-H "Content-Type: application/x-tar" \
	-T "tests/$SHA.tar" "$BASE/$SECRET/$NAME/invalid.tar"

curl $CURLARGS -X PUT \
	-H "Content-Type: application/x-tar" \
	-T "tests/$SHA.tar" \
	"$BASE/$SECRET/$NAME/0000000000000000000000000000000000000000.tar"

curl $CURLARGS -X GET "$BASE/$SECRET/four-oh-four"

curl $CURLARGS -X GET "$BASE/$SECRET/$NAME"

curl $CURLARGS -X GET "$BASE/$SECRET/four-oh-four/four-oh-four.sh"

curl $CURLARGS -X GET "$BASE/$SECRET/four-oh-four/wrong.sh"

curl $CURLARGS -X GET "$BASE/$SECRET/$NAME/$NAME.sh"

curl $CURLARGS -X GET "$BASE/$SECRET/four-oh-four/user-data.sh"

curl $CURLARGS -X GET "$BASE/$SECRET/$NAME/user-data.sh"

curl $CURLARGS -X GET \
	"$BASE/$SECRET/$NAME/0000000000000000000000000000000000000000.tar"

curl $CURLARGS -X GET "$BASE/$SECRET/$NAME/$SHA.tar"
