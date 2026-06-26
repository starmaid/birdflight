import cv2 as cv
import numpy as np
from multiprocessing import Process, shared_memory, Value, Array, Queue
from ctypes import Structure, c_int32, c_bool, c_char_p
import os
import time
from traceback import format_exc

MAX_FRAMES_RENDER = 500
SHARED_STRING_LEN = 200
DEBUG_CV_IMSHOW = False

# Spawn processes to work on images
# give arguments with folders and filenames etc
# access process info via string names (uuid)
# optional: kill process via string name


class bgenManager:
    def __init__(self):
        self.allWorkers = {
            "example_name": {
                "handle": None,
                "isDone": False,
                "hasError": False,
                "errorString": "",
                "startTime": 0,
                "totalFrames": 0,
                "currentFrame": 0,
            }
        }
        return        

    def startWorker(self, worker_name, worker_filepath):

        if worker_name in self.allWorkers.keys():
            # if this user already has a job, kill it and start a new one
            self.killWorker(worker_name)

        isdone = Value(c_bool, False)
        haserror = Value(c_bool, False)
        totalframes = Value(c_int32, 0)
        currframe = Value(c_int32, 0)
        # errorString = Value(c_char_p, bytes("x"*SHARED_STRING_LEN, 'ascii'))
        infoString = Array("c", SHARED_STRING_LEN)
        infoString.value = b"Initializing"
        errorString = Array("c", SHARED_STRING_LEN)
        errorString.value = b"no error"

        cmd_queue = Queue()

        worker_videoname = getInputFile(worker_filepath)

        w = bgenWorker(
            isdone,
            haserror,
            totalframes,
            currframe,
            infoString,
            errorString,
            worker_filepath,
            worker_videoname,
            cmd_queue,
        )

        # after this point, the class is copied to the new process. Only values with shared memory can be accessed
        bgenworkerproc = Process(target=w.start, args=(), daemon=True)
        bgenworkerproc.start()

        self.allWorkers[worker_name] = {
            "handle": bgenworkerproc,
            "isDone": isdone,
            "hasError": haserror,
            "infoString": infoString,
            "errorString": errorString,
            "startTime": int(time.time()),
            "totalFrames": totalframes,
            "currentFrame": currframe,
            "command_queue": cmd_queue,
        }

        return

    def sendCommand(self, worker_name, command, args=None):
        if worker_name in self.allWorkers:
            self.allWorkers[worker_name]["command_queue"].put((command, args))
            return True
        return False

    def cullWorkers(self):
        """Call this every once in a while to remove known workers from the list"""
        workernames = [str(a) for a in self.allWorkers.keys()]
        for worker_name in workernames:
            if worker_name not in self.allWorkers.keys():
                continue
            t = self.allWorkers[worker_name]
            worker_active_time = time.time() - t["startTime"]

            if t["isDone"] == True and worker_active_time > 100:
                # remove completed workers that are 100 seconds old
                self.killWorker(worker_name)
            elif t["isDone"] == False and worker_active_time > 600:
                # kill workers that havent finished that are 10 min old
                self.killWorker(worker_name)
            else:
                continue

        return

    def killWorker(self, worker_name):
        if worker_name in self.allWorkers.keys():
            if self.allWorkers[worker_name]["handle"]:
                self.allWorkers[worker_name]["handle"].kill()
            self.allWorkers.pop(worker_name)
            return True
        else:
            return False


class sharedbgenData(Structure):
    fields = []


class bgenWorker:
    def __init__(
        self,
        isdone,
        haserror,
        totalframes,
        currframe,
        infoString,
        errorString,
        folderpath,
        videofilename,
        command_queue,
    ):
        self.isdone = isdone
        self.haserror = haserror
        self.infoString = infoString
        self.errorString = errorString
        self.folderpath = folderpath

        self.totalframes = totalframes
        self.currframe = currframe
        self.command_queue = command_queue

        self.videopath = os.path.normpath(f"{folderpath}/{videofilename}")
        self.imgpath = os.path.normpath(f"{folderpath}/out.png")

        self.skip_frames = 5

        self.frame_diff_threshold = 50
        self.background_diff_threshold = 50
        self.denoise_radius = 4

        self.stabilized_frames = None

        return

    def clipTo8bit(self, input, allowzero=True):
        lowerlimit = 0
        if not allowzero:
            lowerlimit = 1
        if input < lowerlimit:
            return lowerlimit
        if input > 255:
            return 255
        return int(input)

    def setinfostring(self, content):
        self.infoString.value = bytes(content[:SHARED_STRING_LEN], "ascii")

    def start(self):
        # try to open the file first
        ret = self.openfile()
        if not ret:
            return

        self.setinfostring("Saving first frame")
        self.saveFirstFrame()
        self.setinfostring("Idle")

        # Event loop to keep the process alive
        while True:
            task = self.command_queue.get()
            if task is None:
                break

            cmd, args = task
            self.isdone.value = False
            self.haserror.value = False

            if cmd == "stabilize":
                self.setinfostring("Stabilizing footage")
                self.stabilize()
            elif cmd == "average":
                self.setinfostring("Computing average pixel colors")
                self.getAverageFrame()
            elif cmd == "layer":
                self.setinfostring("Applying effect")
                if args:
                    self.setParams(args.get("skip_frames", self.skip_frames), args.get("img_tweak_params", {}))
                self.layering()
            elif cmd == "doEverything":
                self.doEverything()
            elif cmd == "exit":
                break

            self.isdone.value = True
            self.setinfostring("Idle")
            
        if hasattr(self, '_cap') and self._cap is not None:
            self._cap.release()

    def setParams(self, skip_frames, img_tweak_params):
        self.skip_frames = skip_frames

        self.img_tweak_params = img_tweak_params
        """
        img_tweak_params = {"frame_diff_threshold": 50,
                        "background_diff_threshold": 50,
                        "denoise_radius": 4}
        """

        if "frame_diff_threshold" in img_tweak_params.keys():
            self.frame_diff_threshold = self.clipTo8bit(
                img_tweak_params["frame_diff_threshold"]
            )

        if "background_diff_threshold" in img_tweak_params.keys():
            self.background_diff_threshold = self.clipTo8bit(
                img_tweak_params["background_diff_threshold"]
            )

        if "denoise_radius" in img_tweak_params.keys():
            self.denoise_radius = self.clipTo8bit(
                img_tweak_params["denoise_radius"], False
            )

    def doEverything(self):
        self.setinfostring("Stabilizing footage")
        self.stabilize()
        self.setinfostring("Computing average pixel colors")
        self.getAverageFrame()
        self.setinfostring("Applying effect")
        self.layering()
        self.setinfostring("Complete")


    def stabilize(self):
        """stabilize and preprocess the video"""

        self.stabilized_frames = np.zeros((self._length, self._h, self._w, 3), np.uint8)

        for frame_num in range(self._length):
            ret, frame = self._cap.read()
            if not ret:
                # return with error
                self.haserror.value = True
                break

            if frame_num == 0:
                # do first frame stuff
                # tracking stuff
                prev_gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
                prev_pts = cv.goodFeaturesToTrack(
                    prev_gray,
                    maxCorners=200,
                    qualityLevel=0.01,
                    minDistance=15.0,
                    blockSize=3,
                )

            curr_gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

            try:
                curr_pts, status, err = cv.calcOpticalFlowPyrLK(
                    prev_gray, curr_gray, prev_pts, None
                )
            except:
                self.errorString.value = bytes("stabilization crash", "ascii")
                return

            # Filter only valid points
            idx = np.where(status == 1)[0]
            prev_pts = prev_pts[idx]
            curr_pts = curr_pts[idx]

            # Find transformation matrix
            m, ret = cv.estimateAffinePartial2D(np.array(curr_pts), np.array(prev_pts))

            # Extract translation
            dx = m[0, 2]
            dy = m[1, 2]

            # Extract rotation angle
            da = np.arctan2(m[1, 0], m[0, 0])

            m = np.zeros((2, 3), np.float32)
            m[0, 0] = np.cos(da)
            m[0, 1] = -np.sin(da)
            m[1, 0] = np.sin(da)
            m[1, 1] = np.cos(da)
            m[0, 2] = dx
            m[1, 2] = dy

            # Apply affine wrapping to the given frame
            frame_stabilized = cv.warpAffine(frame, m, (self._w, self._h))

            self.stabilized_frames[frame_num] = frame_stabilized

            prev_frame = frame_stabilized
            prev_gray = cv.cvtColor(prev_frame, cv.COLOR_BGR2GRAY)
            prev_pts = cv.goodFeaturesToTrack(
                prev_gray,
                maxCorners=200,
                qualityLevel=0.01,
                minDistance=15.0,
                blockSize=3,
            )

            self.currframe.value = frame_num

    def layering(self):
        try:
            success = False
            frame_num = 0

            for frame in self.stabilized_frames:
                # print(frame_num)
                if frame_num == 0:
                    # do first frame stuff
                    prev_frame = frame  # .astype(np.float32, copy=False)

                    prev_thresh = np.zeros(
                        (self._h, self._w), dtype=np.uint8
                    )  # float32)
                    prev_thresh_sub = prev_thresh
                    prev2_thresh = prev_thresh

                    # save the current output composite as the first frame
                    composite = frame  # .astype(np.float32, copy=False)

                    frame_num = 1

                    # skip everything and go to next frame
                    continue

                if frame_num % self.skip_frames != 0:
                    # just skip it
                    frame_num += 1
                    continue

                frame_stabilized = frame  # .astype(np.float32, copy=False)

                # calculate difference from previous frame to current frame
                diff = cv.absdiff(frame_stabilized, prev_frame)
                ret, thresh_prevframe = cv.threshold(
                    diff, self.frame_diff_threshold, 255, cv.THRESH_BINARY
                )

                # turn that into an actual 0-1 mask by making grayscale and thresholding again
                thresh_prevframe_grayscale = cv.cvtColor(
                    thresh_prevframe, cv.COLOR_BGR2GRAY
                )
                ret, thresh_prevframe_grayscale = cv.threshold(
                    thresh_prevframe_grayscale, 10, 255, cv.THRESH_BINARY
                )

                # subtract previous two masks from this one
                thresh_sub = cv.subtract(thresh_prevframe_grayscale, prev_thresh)
                thresh_sub = cv.subtract(thresh_sub, prev2_thresh)

                # Create a mask based on the difference from each pixel's average color
                background_diff = cv.absdiff(frame_stabilized, self._background)
                ret, thresh_background = cv.threshold(
                    background_diff,
                    self.background_diff_threshold,
                    255,
                    cv.THRESH_BINARY,
                )  # cv.THRESH_BINARY_INV)

                # turn that into an actual 0-1 mask by making grayscale and thresholding again
                thresh_background_grayscale = cv.cvtColor(
                    thresh_background, cv.COLOR_BGR2GRAY
                )
                ret, thresh_background_grayscale = cv.threshold(
                    thresh_background_grayscale, 10, 255, cv.THRESH_BINARY
                )

                # just ad them together
                combined_thresh = cv.add(thresh_sub, thresh_background_grayscale)

                # remove speckles
                # if set to 1, don't do this to save time
                if self.denoise_radius > 1:
                    se1 = cv.getStructuringElement(
                        cv.MORPH_ELLIPSE, (self.denoise_radius, self.denoise_radius)
                    )
                    se2 = cv.getStructuringElement(
                        cv.MORPH_ELLIPSE, (self.denoise_radius, self.denoise_radius)
                    )
                    mask = cv.morphologyEx(combined_thresh, cv.MORPH_OPEN, se2)
                    mask = cv.morphologyEx(mask, cv.MORPH_CLOSE, se1)
                else:
                    mask = combined_thresh

                # Do this for smooth alpha blends, at the cost of like +20% time
                # alpha = (mask.astype(np.float32) / 255.0)[..., None]
                # composite *= (1.0 - alpha)
                # composite += alpha * frame_stabilized

                # Do this if the mask is 0 or 1 only
                cv.copyTo(frame_stabilized, mask, composite)

                # do last stuff

                # save curent values as prevs
                prev_frame = frame_stabilized
                prev2_thresh = prev_thresh
                prev_thresh = thresh_prevframe_grayscale
                prev_thresh_sub = thresh_sub

                # only show the opencv window if this mode is on.
                if DEBUG_CV_IMSHOW:
                    cv.imshow("frame", mask)
                    k = cv.waitKey(1) & 0xFF
                    if k == ord("q"):
                        break
                    elif k == ord("w"):
                        time.sleep(5)

                # save to the out image. dont do this it adds so much time
                # cv.imwrite(self.imgpath,composite)
                success = True
                frame_num += 1
                self.currframe.value = frame_num

            if success:
                # also archive a copy when done
                result = np.clip(composite, 0, 255).astype(np.uint8)
                cv.imwrite(self.imgpath, result)
                cv.imwrite(f"{self.imgpath}_{int(time.time())}.png", result)

        except Exception as e:
            print("Error generating image")
            print(format_exc())
            try:
                err_string = f"Total Frames: {self._length} Frame on Error: {frame_num}"
                print(err_string)
                self.errorString.value = bytes(err_string[:SHARED_STRING_LEN], "ascii")
            except:
                print("Error printing info string")
                print(format_exc())
            self.haserror.value = True

        if DEBUG_CV_IMSHOW:
            cv.destroyAllWindows()

        return

    def openfile(self):
        # try to open the file first
        try:
            self._cap = cv.VideoCapture(self.videopath)
            self._length = int(self._cap.get(cv.CAP_PROP_FRAME_COUNT))
        except:
            print("unable to open video")
            print(format_exc())
            self.haserror.value = True
            self.isdone.value = True
            return False

        if self._length > MAX_FRAMES_RENDER:
            self._length = MAX_FRAMES_RENDER

        self.totalframes.value = self._length

        self.num_frames_after_skips = int(self._length / self.skip_frames) + 1

        # Get width and height of video stream
        self._w = int(self._cap.get(cv.CAP_PROP_FRAME_WIDTH))
        self._h = int(self._cap.get(cv.CAP_PROP_FRAME_HEIGHT))

        return True

    def getAverageFrame(self):
        frame_output = np.mean(self.stabilized_frames, axis=0, dtype=np.float32).astype(
            np.uint8
        )

        out_path = os.path.normpath(f"{self.folderpath}/out_avgframe.png")
        cv.imwrite(out_path, frame_output)

        self._background = frame_output
        return frame_output

    def saveFirstFrame(self):
        """Opens the first frame of the video and saves it to a file."""
        try:
            cap = cv.VideoCapture(self.videopath)
            ret, frame = cap.read()
            if ret:
                out_path = os.path.normpath(f"{self.folderpath}/out_first.png")
                cv.imwrite(out_path, frame)
            cap.release()
            return ret
        except Exception as e:
            print("Error saving first frame")
            print(format_exc())
            return False


def getInputFile(folderpath):
    for fname in os.listdir(folderpath):
        if "in." in fname:
            # return(f'{folderpath}/{fname}')
            return fname
    return None
