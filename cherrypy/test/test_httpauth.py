from cherrypy.test import test
test.prefer_parent_path()

import md5

import cherrypy
from cherrypy.lib import httpauth

def setup_server():
    class Root:
        def index(self):
            return "This is public."
        index.exposed = True

    class DigestProtected:
        def index(self):
            return "Hello %s, you've been authorized." % cherrypy.request.login
        index.exposed = True

    class BasicProtected:
        def index(self):
            return "Hello %s, you've been authorized." % cherrypy.request.login
        index.exposed = True

    def fetch_users():
        return {'test': 'test'}

    conf = {'/digest': {'tools.digest_auth.on': True,
                        'tools.digest_auth.realm': 'localhost',
                        'tools.digest_auth.users': fetch_users},
            '/basic': {'tools.basic_auth.on': True,
                       'tools.basic_auth.realm': 'localhost',
                       'tools.basic_auth.users': {'test': md5.new('test').hexdigest()}}}
    root = Root()
    root.digest = DigestProtected()
    root.basic = BasicProtected()
    cherrypy.tree.mount(root, config=conf)
    cherrypy.config.update({'environment': 'test_suite'})

from cherrypy.test import helper

class HTTPAuthTest(helper.CPWebCase):

    def testPublic(self):
        self.getPage("/")
        self.assertStatus('200 OK')
        self.assertHeader('Content-Type', 'text/html')
        self.assertBody('This is public.')

    def testBasic(self):
        self.getPage("/basic/")
        self.assertStatus('401 Unauthorized')
        self.assertHeader('WWW-Authenticate', 'Basic realm="localhost"')

        self.getPage('/basic/', [('Authorization', 'Basic dGVzdDp0ZX60')])
        self.assertStatus('401 Unauthorized')
        
        self.getPage('/basic/', [('Authorization', 'Basic dGVzdDp0ZXN0')])
        self.assertStatus('200 OK')
        self.assertBody("Hello test, you've been authorized.")

    def testDigest(self):
        self.getPage("/digest/")
        self.assertStatus('401 Unauthorized')
        
        value = None
        for k, v in self.headers:
            if k.lower() == "www-authenticate":
                if v.startswith("Digest"):
                    value = v
                    break

        if value is None:
            self._handlewebError("Digest authentification scheme was not found")

        value = value[7:]
        items = value.split(', ')
        tokens = {}
        for item in items:
            key, value = item.split('=')
            tokens[key.lower()] = value
            
        missing_msg = "%s is missing"
        bad_value_msg = "'%s' was expecting '%s' but found '%s'"
        nonce = None
        if 'realm' not in tokens:
            self._handlewebError(missing_msg % 'realm')
        elif tokens['realm'] != '"localhost"':
            self._handlewebError(bad_value_msg % ('realm', '"localhost"', tokens['realm']))
        if 'nonce' not in tokens:
            self._handlewebError(missing_msg % 'nonce')
        else:
            nonce = tokens['nonce'].strip('"')
        if 'algorithm' not in tokens:
            self._handlewebError(missing_msg % 'algorithm')
        elif tokens['algorithm'] != '"MD5"':
            self._handlewebError(bad_value_msg % ('algorithm', '"MD5"', tokens['algorithm']))
        if 'qop' not in tokens:
            self._handlewebError(missing_msg % 'qop')
        elif tokens['qop'] != '"auth"':
            self._handlewebError(bad_value_msg % ('qop', '"auth"', tokens['qop']))

            # now let's see if what 
        base_auth = 'Digest username="test", realm="localhost", nonce="%s", uri="/digest/", algorithm=MD5, response="%s", qop=auth, nc=%s, cnonce="1522e61005789929"'

        auth = base_auth % (nonce, '', '00000001')
                
        params = httpauth.parseAuthorization(auth)
        response = httpauth._computeDigestResponse(params, 'test')
        
        auth = base_auth % (nonce, response, '00000001')
        self.getPage('/digest/', [('Authorization', auth)])
        self.assertStatus('200 OK')
        self.assertBody("Hello test, you've been authorized.")
            
if __name__ == "__main__":
    setup_server()
    helper.testmain()