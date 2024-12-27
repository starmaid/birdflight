# app.py
# This file runs the flask webserver

import json
import os
import subprocess

from flask import Flask, render_template, request, redirect, url_for, send_file
from waitress import serve

app = Flask(__name__)
listener = None
sender = None

# PAGES: endpoints that return webpages =======================================

@app.route('/')
def index():
    """
    The homepage. Network graph and data preview.
    """
    global listener
    text = None
    image = None
    if listener is not None:
        # we have some data to preview
        d = listener.getData()
        print(d)
        if d['type'] == 'txt':
            text = d['data'] 
        # TODO handle and implement more types of data
    
    return render_template('index.html', isdebug=config['debug'],text=text,image=image)

        

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




# USER API: For the user's program to interact with ===========================

@app.route('/getdata', methods=['GET'])
def getdata():
    global listener
    if listener is None:
        # Theres no listener, so whatever.
        d = {'connected': False}
    else:
        d = listener.getData()
    return d


@app.route('/setdata', methods=['POST'])
def setdata():
    if request.method == 'POST':
        #print(request.form)
        try:
            r = request.form.to_dict()
        except:
            data = request.form
            r = str(request.values)

        print(r)
        if r is not None:
            if 'data' not in r.keys():
                # this means just accept the whole thing. who cares
                data = str(r)
                pass
            else:
                data = r['data']
                if 'b64encoded' in r.keys():
                    try:
                        encoded = bool(r['b64encoded'])
                    except:
                        encoded = False
                else:
                    encoded = False
                if 'type' in r.keys():
                    dtype = str(r['type'])
                else:
                    dtype = 'txt'
        else:
            encoded = False
            dtype = 'txt'
            pass
        
        global sender
        global listener
        if sender is None:
            d = {'connected': False}
        else:
            if listener is not None:
                chain = listener.header['chain']
                if chain[0] == config['hostname']:
                    chain.pop(0)
                chain.append(config['hostname'])
            else:
                chain = [config['hostname']]

            print(' '.join([str(v) for v in [data, dtype, chain, encoded]]))
            success = sender.setData(data, dtype, chain, encoded)
            d = {'connected': success}
        
        return d
    else:
        return 'Endpoint only accepts POST'


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
