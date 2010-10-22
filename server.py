#! /usr/bin/env python
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from uuid import uuid4
from base64 import b64decode
from urlparse import urlparse, parse_qs, urlunparse
from urllib import urlencode
import os
from string import Template
import s3_post
import mimetypes

FORM_TEMPLATE = Template(open('templates/root.template', 'rb').read())
UPLOAD_COMPLETE_TEMPLATE = Template(open('templates/upload_complete.template',
    'rb').read())
UPLOADIFY_SCRIPT_TEMPLATE = Template(open('templates/uploadify_script.template',
    'rb').read())

BUCKET_NAME = 'edacloud_media_test'

class MyHandler(BaseHTTPRequestHandler):
    def generate_upload_form(self):
        key = uuid4().hex
        s3_post_args = s3_post.get_post_args(BUCKET_NAME, key)  
    
        # assemble the scriptData dictionary string for uploadify's use
        scriptData = ['{']
        for field in s3_post_args['fields']:
            # apparently there's some extra uri decoding going on with
            #   uploadify/flash/javascript
            #   so, to protect the values, we need to doubly encode them
            #   sigh;
            #   see for example:
            #     http://www.uploadify.com/forum/viewtopic.php?f=7&t=1416
            encoding_string = "encodeURIComponent(encodeURIComponent('{0}'))" 
            encoded_value = encoding_string.format(field['value'])
            keyValue = "'{0}' : {1},".format(field['name'], encoded_value) 
            scriptData.append(keyValue)
            if field['name'] == 'policy':
                # save the policy value for debug
                policy = field['value']
            if field['name'] == 'signature':
                # save the signature value for debug
                signature = field['value']
        scriptData.append('}')

        success_action_redirect=urlunparse((
                'http',
                '{0}:{1}'.format(
                    self.server.server_name, self.server.server_port),
                'upload_complete',
                '',
                urlencode(dict(bucket=BUCKET_NAME, key=key, etag='')),
                ''))
        # generate the javascript for uploadify
        uploadify_script = UPLOADIFY_SCRIPT_TEMPLATE.safe_substitute(dict( 
            scriptData='\n'.join(scriptData), action=s3_post_args['action'],
            success_action_redirect=success_action_redirect))

        # assemble the dictionary for template interpolation
        d = {
            'hostname': self.server.server_name,
            'port' : self.server.server_port,
            'action' : s3_post_args['action'],
            'key' : key,
            'policy' : b64decode(policy), # for debug
            'script' : uploadify_script, 
            'signature' : signature,
        }
        self.wfile.write(FORM_TEMPLATE.safe_substitute(d))
        return

    def upload_complete(self):
        parsed = urlparse(self.path)
        d = parse_qs(parsed.query)
        for k in d:
            d[k] = d[k][0] # take the first element of each qs list
        self.wfile.write(UPLOAD_COMPLETE_TEMPLATE.safe_substitute(d))
        return

    def do_GET_upload_complete(self):
        self.send_response(200)
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.upload_complete()

    def do_GET_root(self):
        self.send_response(200)
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.generate_upload_form()

    def do_GET_file(self):
        # assume it's a file
        filename = os.path.join('www', self.path[1:])
        if os.path.exists(filename):
            self.send_response(200)
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Content-Type', mimetypes.guess_type(filename)[0])
            self.end_headers()
            self.wfile.write(open(filename, 'rb').read())
        else:
            self.send_response(404)

    def do_GET(self):
        if 'upload_complete' in self.path:
            self.do_GET_upload_complete()
        elif '/' == self.path:
            self.do_GET_root()
        else:
            self.do_GET_file()
        self.wfile.close()
        return

def main():
    server = HTTPServer(('', 8080), MyHandler)
    print 'HTTP Server starting on {0}:{1}'.format(server.server_name,
        server.server_port)
    server.serve_forever()

if __name__ == '__main__':
    main()



