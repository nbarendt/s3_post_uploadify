#! /usr/bin/env python
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from boto import connect_s3
from uuid import uuid4
from ConfigParser import SafeConfigParser
from base64 import b64decode
from urlparse import urlparse, parse_qs

# read the AWS S3 Credentials in from the ini file
config = SafeConfigParser()
config.read('server.ini')
# create an S3 Boto connection
conn = connect_s3(config.get('s3', 'access'), config.get('s3', 'secret'))

FORM_TEMPLATE = u"""
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
</head>
<body>

    <p>
        Key: {key}
    </p>
    <p>
        Decoded Policy: {policy}
    </p>
    <form action="{action}" method="post" enctype="multipart/form-data">
        {hidden_fields}
        <br/>
        <!-- file must be last field -->
        File: <input type="file" name="file"/> <br/>
        <input type="submit" name="submit" value="Submit"/> 
    </form>
</body>
</html>
"""

UPLOAD_COMPLETE_TEMPLATE = u"""
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
</head>
<body>
    Successfully uploaded Key "{key}" <br/> to Bucket "{bucket}" <br/> (etag = {etag})!
</body>
</html>
"""

BUCKET_NAME = 'edacloud_media_test'

class MyHandler(BaseHTTPRequestHandler):
    def generate_upload_form(self):
        key = uuid4().hex
        s3_post_args = conn.build_post_form_args(bucket_name=BUCKET_NAME,
            key=key,
            expires_in=6000,
            success_action_redirect='http://{0}:{1}/upload_complete'.format(
                self.server.server_name, self.server.server_port))
        hidden_fields = ''
        for field in s3_post_args['fields']:
            hidden_fields += ' '.join(['<input',
                                    'type="hidden"',
                                    'name="{0}" value="{1}"'.format(
                                        field['name'], field['value']),
                                    '/>\n'])
            if field['name'] == 'policy':
                policy = field['value']
    
        d = {
            'hostname': self.server.server_name,
            'port' : self.server.server_port,
            'hidden_fields' : hidden_fields,
            'action' : s3_post_args['action'],
            'key' : key,
            'policy' : b64decode(policy),
        }
            
        self.wfile.write(FORM_TEMPLATE.format(**d))
        return

    def upload_complete(self):
        parsed = urlparse(self.path)
        d = parse_qs(parsed.query)
        for k in d:
            d[k] = d[k][0] # take the first element of each qs list
        self.wfile.write(UPLOAD_COMPLETE_TEMPLATE.format(**d))
        return
 
    def do_GET(self):
        if 'upload_complete' in self.path:
            self.upload_complete()
        else:
            self.generate_upload_form()

def main():
    server = HTTPServer(('', 8080), MyHandler)
    print 'HTTP Server starting on {0}:{1}'.format(server.server_name,
        server.server_port)
    server.serve_forever()

if __name__ == '__main__':
    main()



