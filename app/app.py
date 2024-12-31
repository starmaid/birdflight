# app.py
# This file runs the flask webserver

import json
import os
import subprocess
import uuid as uuidlib
import time

from flask import Flask, render_template, request, make_response, redirect, url_for, send_file
from waitress import serve

import ipinfo

import birdgen

handler = ipinfo.getHandler()
birdManager = birdgen.bgenManager()

app = Flask(__name__)
listener = None
sender = None

# PAGES: endpoints that return webpages =======================================

@app.route('/', methods=['GET','POST'])
def index():
    """
    The homepage. Network graph and data preview.
    """

    if request.method == 'GET':

        uuid = request.cookies.get('UUID')

        if uuid is None:
            prev_image = None
        else:
            prev_image = f"/static/user/{uuid}/out.png?{int(time.time())}"

        print(request.cookies.get('UUID'))
        return render_template('index.html', 
                                error=None,
                                preview_img=prev_image)

    elif request.method == 'POST':
        #print(request.form)
        try:
            r = request.form.to_dict()
        except:
            data = request.form
            r = str(request.values)
        #print(r)

        (uuid, filepath) = getUserFolder(request)

        # start the worker
        birdManager.startWorker(uuid, filepath, int(r['range1slider']), int(r['range2slider']))

        resp = make_response(render_template('index.html',
                                error=None,
                                preview_img=f"/static/user/{uuid}/out.png?{int(time.time())}"))
        resp.set_cookie('UUID', uuid)
        
        return resp


def getUserFolder(request):
    global handler

    ip = request.remote_addr
    ipdetails = handler.getDetails(ip)

    uuid = request.cookies.get('UUID')
    if uuid is None:
        # then we have to make a new one
        uuid = str(uuidlib.uuid4())

    filepath = os.path.normpath(f'{app.root_path}/static/user/{uuid}')
    meta_filepath = os.path.normpath(f'{filepath}/meta.json')

    try:
        os.makedirs(filepath)
    except:
        pass
    
    if os.path.exists(meta_filepath):
        with open(meta_filepath,'r') as fp:
            meta = json.load(fp)
        
        meta['LAST_REQUEST'] = int(time.time())
        meta['NUM_REQUESTS'] += 1

        with open(meta_filepath,'w') as fp:
            json.dump(meta,fp)
    else:
        meta = {}
        meta['IP_ADDRESS'] = ip
        try:
            meta['IP_COUNTRY'] = ipdetails.all['country']
        except:
            meta['IP_COUNTRY'] = 'UNK'
        
        try:
            meta['IP_CITY'] = ipdetails.all['city']
        except:
            meta['IP_COUNTRY'] = 'UNK'

        meta['LAST_REQUEST'] = int(time.time())
        meta['NUM_REQUESTS'] = 1

        with open(meta_filepath,'w') as fp:
            json.dump(meta,fp)

    return(uuid,filepath)


@app.route('/api/upload', methods=['POST'])
def upload():
    """
    upload and save video
    """
    message = None

    (uuid, filepath) = getUserFolder(request)

    meta_filepath = os.path.normpath(f'{filepath}/meta.json')
    video_filepath = os.path.normpath(f'{filepath}/meta.json')

    if 'videofile' in request.files.keys() and request.files['videofile'].filename != '':
        
        newfile = request.files['videofile']

        print(newfile)

        # this is always zero??....
        if newfile.content_length > 10000000:
            message = "File too large. Try cropping or downscaling the video first."
        else:
            user_filename = newfile.filename
            extension = user_filename.split('.')[-1]

            newpath = os.path.join(app.root_path,
                os.path.normpath(f'./static/user/{uuid}/in.{extension}'))

            fcontent = newfile.read()

            with open(newpath,'wb') as f:
                # Sanitize CR out
                f.write(fcontent)
            
            message = f"successfully uploaded {newfile.filename} ({newfile.content_length} bytes)"
        
    else:
        message = "unable to process file"

    resp = make_response(render_template('index.html',
                                error=message))
    resp.set_cookie('UUID', uuid)
        
    return resp

@app.route('/info')
def info():
    """
    Version, your own pubkey, and other info
    """
    global version

    return render_template('info.html',
        version=version,
        hostname=config['hostname'],
        )

@app.route('/imgview')
def imgview():
    """
    
    """
    uuid = request.cookies.get('UUID')

    return render_template('imgview.html',
        preview_img=f"/static/user/{uuid}/out.png?{int(time.time())}")


# NON-PAGE HELPERS: do other tasks in the program =============================

def loadConfig():
    with open('./app/data/config.json', 'r') as c:
        try:
            config = json.load(c)
        except:
            print('unable to load config. Exiting')
            config = None
    return config




if __name__ == '__main__':
    # Load config

    config = loadConfig()
    version = subprocess.check_output("git describe --tags", shell=True).decode().strip().split('-')[0]

    # start web server
    if config is not None:
        if config['debug']:
            app.run(debug=True, port=config['flaskport'])
        else:
            # This is the 'production' WSGI server
            serve(app, port=config['flaskport'])
