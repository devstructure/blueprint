from flask.testing import FlaskClient
import json
import os.path
import sys

from blueprint.io.server import app

SECRET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_-'
NAME = 'test'
SHA = 'adff242fbc01ba3753abf8c3f9b45eeedec23ec6'

filename = '{0}.tar'.format(SHA)
pathname = os.path.join(os.path.dirname(__file__), 'tests', filename)

c = app.test_client()

def test_GET_secret():
    response = c.get('/secret')
    assert 201 == response.status_code
    assert 64 + 1 == len(response.data)

def test_PUT_blueprint_invalid_secret():
    response = c.put('/{0}/{1}'.format('invalid', NAME),
                     content_type='application/json',
                     data=json.dumps({}))
    assert 400 == response.status_code

def test_PUT_blueprint_invalid_name():
    response = c.put('/{0}/{1}'.format(SECRET, '%20'),
                     content_type='application/json',
                     data=json.dumps({}))
    assert 400 == response.status_code

def test_PUT_blueprint_invalid_syntax_data():
    response = c.put('/{0}/{1}'.format(SECRET, NAME),
                     content_type='application/json',
                     data='}{')
    assert 400 == response.status_code

def test_PUT_blueprint_invalid_schema_data():
    response = c.put('/{0}/{1}'.format(SECRET, NAME),
                     content_type='application/json',
                     data=json.dumps({'invalid': 'invalid'}))
    assert 400 == response.status_code

def test_PUT_blueprint_invalid_length_data():
    response = c.put('/{0}/{1}'.format(SECRET, NAME),
                     content_type='application/json',
                     data=json.dumps({
                         'files': {
                             '/etc/long': '.' * 65 * 1024 * 1024,
                         },
                     }))
    assert 413 == response.status_code

def test_PUT_blueprint_empty():
    response = c.put('/{0}/{1}'.format(SECRET, NAME),
                     content_type='application/json',
                     data=json.dumps({}))
    assert 202 == response.status_code

def test_PUT_tarball_empty():
    test_PUT_blueprint_empty()
    response = c.put('/{0}/{1}/{2}.tar'.format(SECRET, NAME, SHA),
                     content_type='application/x-tar',
                     data=open(pathname).read())
    assert 400 == response.status_code

def test_PUT_blueprint_sources():
    response = c.put('/{0}/{1}'.format(SECRET, NAME),
                     content_type='application/json',
                     data=json.dumps({
                         'sources': {
                             '/usr/local': filename,
                         },
                     }))
    assert 202 == response.status_code

def test_PUT_tarball_invalid_sha():
    test_PUT_blueprint_sources()
    response = c.put('/{0}/{1}/{2}.tar'.format(SECRET, NAME, 'invalid'),
                     content_type='application/x-tar',
                     data=open(pathname).read())
    assert 400 == response.status_code

def test_PUT_tarball_invalid_data():
    test_PUT_blueprint_sources()
    response = c.put('/{0}/{1}/{2}.tar'.format(SECRET, NAME, '0' * 40),
                     content_type='application/x-tar',
                     data=open(pathname).read())
    assert 400 == response.status_code

def test_PUT_tarball_invalid_length_data():
    test_PUT_blueprint_sources()
    response = c.put('/{0}/{1}/{2}.tar'.format(SECRET, NAME, '0' * 40),
                     content_type='application/x-tar',
                     data='.' * 65 * 1024 * 1024)
    assert 413 == response.status_code

def test_PUT_tarball():
    test_PUT_blueprint_sources()
    response = c.put('/{0}/{1}/{2}.tar'.format(SECRET, NAME, SHA),
                     content_type='application/x-tar',
                     data=open(pathname).read())
    assert 202 == response.status_code

def test_GET_blueprint_invalid():
    test_PUT_blueprint_empty()
    response = c.get('/{0}/{1}'.format(SECRET, 'four-oh-four'))
    assert 404 == response.status_code

def test_GET_blueprint():
    test_PUT_blueprint_empty()
    response = c.get('/{0}/{1}'.format(SECRET, NAME))
    assert 301 == response.status_code

def test_GET_blueprint_sh_invalid():
    test_PUT_blueprint_empty()
    response = c.get('/{0}/{1}/{1}.sh'.format(SECRET, 'four-oh-four'))
    assert 404 == response.status_code

def test_GET_blueprint_sh_mismatch():
    test_PUT_blueprint_empty()
    response = c.get('/{0}/{1}/{2}.sh'.format(SECRET, 'four-oh-four', 'wrong'))
    assert 400 == response.status_code

def test_GET_blueprint_sh():
    test_PUT_blueprint_empty()
    response = c.get('/{0}/{1}/{1}.sh'.format(SECRET, NAME))
    assert 200 == response.status_code
    assert '#!' == response.data[0:2]

def test_GET_blueprint_userdata_invalid():
    response = c.get('/{0}/{1}/user-data.sh'.format(SECRET, 'four-oh-four'))
    assert 404 == response.status_code

def test_GET_blueprint_userdata():
    test_PUT_blueprint_empty()
    response = c.get('/{0}/{1}/user-data.sh'.format(SECRET, NAME))
    assert 200 == response.status_code
    assert '#!' == response.data[0:2]

def test_GET_tarball_invalid():
    test_PUT_blueprint_empty()
    response = c.get('/{0}/{1}/{2}.tar'.format(SECRET, NAME, '0' * 40))
    assert 404 == response.status_code

def test_GET_tarball():
    test_PUT_tarball()
    response = c.get('/{0}/{1}/{2}.tar'.format(SECRET, NAME, SHA))
    assert 301 == response.status_code
