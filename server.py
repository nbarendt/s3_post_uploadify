#! /usr/bin/env python
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from boto import connect_s3
from uuid import uuid4
from ConfigParser import SafeConfigParser
from base64 import b64decode
from urlparse import urlparse, parse_qs, urlunparse
from urllib import urlencode
import os

# read the AWS S3 Credentials in from the ini file
config = SafeConfigParser()
config.read('server.ini')
# create an S3 Boto connection
conn = connect_s3(config.get('s3', 'access'), config.get('s3', 'secret'))

FORM_TEMPLATE = u"""
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <script type="text/javascript" src="jquery.js"></script>
    <script type="text/javascript" src="swfobject.js"></script> 
    <script type="text/javascript" src="jquery.uploadify.v2.1.0.js"></script> 

    <script type="text/javascript">
        {script}
    </script>
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
        File: <input id="fileInput1" type="file" name="fileInput1"/>
            <a href="javascript:$('#fileInput1').uploadifyUpload();">
                Upload File
            </a>
         <br/>
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
            #success_action_redirect='http://{0}:{1}/upload_complete'.format(
            #    self.server.server_name, self.server.server_port),
            fields=[{'name': 'success_action_status',
                     'value': 201}],
            conditions=["['starts-with', '$Filename', '']",
                        "['starts-with', '$folder', '']",
                        "{'success_action_status' : '201'}",]
            )
        
        qs_dict=dict(bucket=BUCKET_NAME, key=key)
        success_action_redirect = urlunparse(
                ('http',
                '{0}:{1}'.format(self.server.server_name,
                    self.server.server_port),
                'upload_complete',
                urlencode(qs_dict),
                '',
                '')
            )
        #success_action_redirect='http://{0}:{1}/upload_complete'.format(
        #    self.server.server_name, self.server.server_port)

        hidden_fields = ''
        for field in s3_post_args['fields']:
            hidden_fields += ' '.join(['<input',
                                    'type="hidden"',
                                    'name="{0}" value="{1}"'.format(
                                        field['name'], field['value']),
                                    '/>\n'])
            if field['name'] == 'policy':
                policy = field['value']
    
        scriptData = '{\n'
        for field in s3_post_args['fields']:
            scriptData += "'{0}': '{1}',\n".format(field['name'],
                field['value'])
        scriptData += '}\n'

        d = {
            'hostname': self.server.server_name,
            'port' : self.server.server_port,
            'hidden_fields' : hidden_fields,
            'action' : s3_post_args['action'],
            'key' : key,
            'policy' : b64decode(policy),
            'script' : u"""
                $(document).ready(function() {
                $("#fileInput1").uploadify({
                    'uploader' : 'uploadify.swf',
                    'cancelImg' : 'cancel.png',
                    'multi' : false,
                    'scriptData': %s, 
                    'script': '%s',
                    'fileDataName' : 'file',
                    'onError' : function(event, queueID, fileObj, errorObj) {
                            if(errorObj.type == 'HTTP'
                                && errorObj.info == 201) {
                                console.log('all ok: HTTP 201');
                            } else if(errorObj.type == 'IO'
                                && errorObj.info == 'Error #2038') {
                                console.log('all ok: IO 2038');
                            } else { 
                                alert("Error: " + errorObj.type + "  Msg: " + errorObj.info)}
    ;
                        },
                    'onComplete' : function(event, queueID, fileObj, response, data){
                            allert("Complete: " + response);
                        },
                    });
                });
""" % (scriptData, s3_post_args['action']), 
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



