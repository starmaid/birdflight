# app.py
# This file runs the flask webserver

import json
import os
import subprocess
import uuid as uuidlib
import time

from flask import (
    Flask,
    render_template,
    request,
    make_response,
    redirect,
    url_for,
    send_file,
    send_from_directory,
    jsonify,
)
from waitress import serve
import ipinfo

import birdgen

handler = ipinfo.getHandler()
birdManager = birdgen.bgenManager()

app = Flask(__name__)
listener = None
sender = None

# PAGES: endpoints that return webpages =======================================


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.route("/", methods=["GET", "POST"])
def index():
    """
    The homepage. Network graph and data preview.
    """

    if request.method == "GET":
        uuid = request.cookies.get("UUID")

        if uuid is None:
            image_paths = None
        else:
            image_paths = {
                "out_first": f"/static/user/{uuid}/out_first.png?{int(time.time())}",
                "out_avgframe": f"/static/user/{uuid}/out_avgframe.png?{int(time.time())}",
                "out": f"/static/user/{uuid}/out.png?{int(time.time())}",
            }

        # print(request.cookies.get('UUID'))
        return render_template("index.html", image_paths=image_paths)


@app.route("/api/stabilize", methods=["POST"])
def stabilize():
    (uuid, filepath) = getUserFolder(request)
    birdManager.sendCommand(uuid, "stabilize")
    return jsonify({"status": "success", "message": "Stabilization started"})


@app.route("/api/layer", methods=["POST"])
def layer():
    if request.method == "POST":
        # print(request.form)
        try:
            r = request.form.to_dict()
        except:
            data = request.form
            r = str(request.values)
        # print(r)

        (uuid, filepath) = getUserFolder(request)

        # extract the image params
        param_img_tweak_params = {
            "frame_diff_threshold": int(r["range2slider"]),
            "background_diff_threshold": int(r["range3slider"]),
            "denoise_radius": int(r["range4slider"]),
        }

        skip_frames = int(r.get("range1slider", 5))
        birdManager.sendCommand(uuid, "layer", {"skip_frames": skip_frames, "img_tweak_params": param_img_tweak_params})
        
        resp = jsonify({
            "status": "success", 
            "message": "Layering started"
        })
        resp.set_cookie("UUID", uuid)

        return resp


def getUserFolder(request):
    global handler

    ip = request.remote_addr
    ipdetails = handler.getDetails(ip)

    uuid = request.cookies.get("UUID")
    if uuid is None:
        # then we have to make a new one
        uuid = str(uuidlib.uuid4())

    filepath = os.path.normpath(f"{app.root_path}/static/user/{uuid}")
    meta_filepath = os.path.normpath(f"{filepath}/meta.json")

    try:
        os.makedirs(filepath)
    except:
        pass

    if os.path.exists(meta_filepath):
        with open(meta_filepath, "r") as fp:
            meta = json.load(fp)

        meta["LAST_REQUEST"] = int(time.time())
        meta["NUM_REQUESTS"] += 1

        with open(meta_filepath, "w") as fp:
            json.dump(meta, fp)
    else:
        meta = {}
        meta["IP_ADDRESS"] = ip
        try:
            meta["IP_COUNTRY"] = ipdetails.all["country"]
        except:
            meta["IP_COUNTRY"] = "UNK"

        try:
            meta["IP_CITY"] = ipdetails.all["city"]
        except:
            meta["IP_COUNTRY"] = "UNK"

        meta["LAST_REQUEST"] = int(time.time())
        meta["NUM_REQUESTS"] = 1
        meta["LIFETIME_UPLOAD"] = 0

        meta["GENERATE"] = {
            "0_uploaded": False,
            "1_filename": "",
            "2_stabilized": False,
            "3_avgcolor": False,
            "4_layered": False,
        }

        with open(meta_filepath, "w") as fp:
            json.dump(meta, fp)

    return (uuid, filepath)


@app.route("/api/upload", methods=["POST"])
def upload():
    """
    upload and save video
    """
    status = "error"
    message = None

    (uuid, filepath) = getUserFolder(request)

    meta_filepath = os.path.normpath(f"{filepath}/meta.json")
    with open(meta_filepath, "r") as fp:
        meta = json.load(fp)

    videoname = birdgen.getInputFile(filepath)

    # delete the last video because the extension might be different
    try:
        os.remove(f"{filepath}/{videoname}")
    except:
        pass

    if (
        "videofile" in request.files.keys()
        and request.files["videofile"].filename != ""
    ):
        newfile = request.files["videofile"]

        file_length = newfile.seek(0, os.SEEK_END)
        newfile.seek(0, os.SEEK_SET)

        # print(newfile)

        # this is always zero??....
        if file_length > 50000000:
            message = "File larger than 50 MB. Try cropping or downscaling the video first. What am I, a video hosting site?"
        elif meta["LIFETIME_UPLOAD"] > 1000000000:
            message = "You have uploaded more than 1GB of video. Please chill out and dm me, I'll take you out of timeout."
        else:
            user_filename = newfile.filename
            extension = user_filename.split(".")[-1]

            newpath = os.path.join(
                app.root_path, os.path.normpath(f"./static/user/{uuid}/in.{extension}")
            )

            fcontent = newfile.read()

            meta["LIFETIME_UPLOAD"] += file_length
            with open(meta_filepath, "w") as fp:
                json.dump(meta, fp)

            with open(newpath, "wb") as f:
                # Sanitize CR out
                f.write(fcontent)

            status = "success"
            message = f"successfully uploaded {newfile.filename} ({file_length} bytes)"
            # start the worker
            birdManager.startWorker(uuid, filepath)

        resp = jsonify({
            "status": "success",
            "message": "Worker started",
            "preview_img": f"/static/user/{uuid}/out.png?{int(time.time())}"
        })

    else:
        message = "unable to process file"

    resp = jsonify({"status": status, "message": message})
    resp.set_cookie("UUID", uuid)

    return resp

@app.route("/api/download", methods=["GET", "POST"])
def download():
    uuid = request.cookies.get("UUID")
    if not uuid:
        return jsonify({"status": "error", "message": "Session not found"}), 400
        
    filepath = os.path.normpath(f"{app.root_path}/static/user/{uuid}/out.png")
    
    if not os.path.exists(filepath):
        return jsonify({"status": "error", "message": "Image not found. Please layer an image first."}), 404

    download_filename = f"birdflight_{int(time.time())}.png"
    
    return send_file(filepath, as_attachment=True, download_name=download_filename)


@app.route("/info")
def info():
    """
    Version, your own pubkey, and other info
    """
    global version

    return render_template(
        "info.html",
        version=version,
        hostname=config["hostname"],
    )


@app.route("/imgview")
def imgview():
    """ """
    uuid = request.cookies.get("UUID")

    if uuid is None:
        image_paths = None
    else:
        image_paths = {
            "out_first": f"/static/user/{uuid}/out_first.png?{int(time.time())}",
            "out_avgframe": f"/static/user/{uuid}/out_avgframe.png?{int(time.time())}",
            "out": f"/static/user/{uuid}/out.png?{int(time.time())}",
        }

    global birdManager

    try:
        workerref = birdManager.allWorkers[uuid]
        error = workerref["hasError"].value
        infoString = workerref["infoString"].value.decode("ascii")
        errorString = workerref["errorString"].value.decode("ascii")
        done = workerref["isDone"].value
        duration = int(time.time()) - workerref["startTime"]
        totalframes = workerref["totalFrames"].value
        currframe = workerref["currentFrame"].value
    except KeyError:
        error = None
        infoString = None
        errorString = None
        done = None
        duration = 0
        totalframes = 0
        currframe = 0

    return render_template(
        "imgview.html",
        image_paths=image_paths,
        isdone=done,
        error=error,
        infoString=infoString,
        errorString=errorString,
        duration=duration,
        totalframes=totalframes,
        currframe=currframe,
    )


# NON-PAGE HELPERS: do other tasks in the program =============================


def loadConfig():
    with open("./app/data/config.json", "r") as c:
        try:
            config = json.load(c)
        except:
            print("unable to load config. Exiting")
            config = None
    return config


if __name__ == "__main__":
    # Load config

    config = loadConfig()
    if config["usegit"]:
        version = (
            subprocess.check_output("git describe --tags", shell=True)
            .decode()
            .strip()
            .split("-")[0]
        )
    else:
        version = "0.1.0"

    # start web server
    if config is not None:
        if config["debug"]:
            app.run(debug=True, host="0.0.0.0", port=config["flaskport"])
        else:
            # This is the 'production' WSGI server
            serve(app, host="0.0.0.0", port=config["flaskport"])
