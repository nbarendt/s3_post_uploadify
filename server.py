#! /usr/bin/env python
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from boto import connect_s3
from uuid import uuid4
from ConfigParser import SafeConfigParser
from base64 import b64decode
from urlparse import urlparse, parse_qs, urlunparse
from urllib import urlencode
import os
from string import Template

FORM_TEMPLATE = Template(open('templates/root.template', 'rb').read())
UPLOAD_COMPLETE_TEMPLATE = TEMPLATE(open('templates/upload_complete.template',
    'rb').read())
UPLOADIFY_SCRIPT_TEMPLATE = Template(open('templates/uploadify_script.template',
    'rb').read())
BUCKET_NAME = 'edacloud_media_test'

def get_s3_connection():
    # read the AWS S3 Credentials in from the ini file
    config = SafeConfigParser()
    config.read('server.ini')
    # create an S3 Boto connection
    return connect_s3(config.get('s3', 'access'), config.get('s3', 'secret'))

def get_post_args(key):
        return get_s3_connection().build_post_form_args(
            bucket_name=BUCKET_NAME,
            key=key,
            expires_in=6000,
            #success_action_redirect='http://{0}:{1}/upload_complete'.format(
            #    self.server.server_name, self.server.server_port),
            fields=[{'name': 'success_action_status',
                     'value': 201}],
            conditions=["['starts-with', '$Filename', '']",
                        "['starts-with', '$folder', '']",
                        "{'success_action_status' : '201'}",]
            )

class MyHandler(BaseHTTPRequestHandler):
    def generate_upload_form(self):
        key = uuid4().hex
        s3_post_args = get_post_args(key)  
    
        # assemble the scriptData string for uploadify's use
        scriptData = '{\n'
        for field in s3_post_args['fields']:
            scriptData += "'{0}': '{1}',\n".format(field['name'],
                field['value'])
            if field['name'] == 'policy':
                # save the policy value for debug
                policy = field['value']
        scriptData += '}\n'

        uploadify_script = UPLOADIFY_SCRIPT_TEMPLATE.safe_substitute(dict( 
            scriptData=scriptData, action=s3_post_args['action']))

        # assemble the dictionary for template interpolation
        d = {
            'hostname': self.server.server_name,
            'port' : self.server.server_port,
            'action' : s3_post_args['action'],
            'key' : key,
            'policy' : b64decode(policy), # for debug
            'script' : uploadify_script, 
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
        print("filename: %s" % filename)
        if os.path.exists(filename):
            self.send_response(200)
            self.send_header('Cache-Control', 'no-cache')
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



