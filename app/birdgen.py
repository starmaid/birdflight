import cv2 as cv
import numpy as np
from multiprocessing import Process, shared_memory, Value, Array
from ctypes import Structure, c_int32, c_bool
import os
import time
from traceback import format_exc

MAX_FRAMES_RENDER = 500
DEBUG_CV_IMSHOW = False

# Spawn processes to work on images
# give arguments with folders and filenames etc
# access process info via string names (uuid)
# optional: kill process via string name


class bgenManager():
    def __init__(self):
        self.allWorkers = {
            "example_name": {
                "handle": None,
                "isDone": False,
                "hasError": False,
                "startTime": 0,
                "totalFrames": 0,
                "currentFrame": 0
            }
        }
        return

    def startWorker(self,worker_name
                            ,worker_filepath
                            ,param_skipframes
                            ,param_bluramount):
        if worker_name in self.allWorkers.keys():
            # if this user already has a job, kill it and start a new one
            self.killWorker(worker_name)

        isdone = Value(c_bool,False)
        haserror = Value(c_bool,False)
        totalframes = Value(c_int32,0)
        currframe = Value(c_int32,0)
        
        worker_videoname = getInputFile(worker_filepath)

        w = bgenWorker(isdone,haserror,totalframes,currframe,worker_filepath,worker_videoname,param_skipframes,param_bluramount)
        
        # after this point, the class is copied to the new process. Only values with shared memory can be accessed
        bgenworkerproc = Process(target=w.start, args=(), daemon=True)
        bgenworkerproc.start()

        self.allWorkers[worker_name] = {
                "handle": bgenworkerproc,
                "isDone": isdone,
                "hasError": haserror,
                "startTime": int(time.time()),
                "totalFrames": totalframes,
                "currentFrame": currframe
            }

        return

    def cullWorkers(self):
        """Call this every once in a while to remove known workers from the list"""
        workernames = [str(a) for a in self.allWorkers.keys()]
        for worker_name in workernames:
            if worker_name not in self.allWorkers.keys():
                continue
            t = self.allWorkers[worker_name]
            worker_active_time = time.time() - t['startTime']

            if t['isDone']==True and worker_active_time > 100:
                # remove completed workers that are 100 seconds old
                self.killWorker(worker_name)
            elif t['isDone']==False and worker_active_time > 600:
                # kill workers that havent finished that are 10 min old
                self.killWorker(worker_name)
            else:
                continue
        
        return

    def killWorker(self,worker_name):
        if worker_name in self.allWorkers.keys():
            if self.allWorkers[worker_name]['handle']:
                self.allWorkers[worker_name]['handle'].kill()
            self.allWorkers.pop(worker_name)
            return(True)
        else:
            return(False)

class sharedbgenData(Structure):
    fields = [

    ]

class bgenWorker():
    def __init__(self,isdone,haserror,totalframes,currframe,folderpath,videofilename,skip_frames,blur_size):
        self.isdone = isdone
        self.haserror = haserror
        self.folderpath = folderpath
        
        self.totalframes = totalframes
        self.currframe = currframe

        self.videopath = os.path.normpath(f'{folderpath}/{videofilename}')
        self.imgpath = os.path.normpath(f'{folderpath}/out.png')

        self.skip_frames = skip_frames
        self.blur_size = blur_size
        return

    def start(self):

        # try to open the file first
        try:
            cap = cv.VideoCapture(self.videopath)
            length = int(cap.get(cv.CAP_PROP_FRAME_COUNT))
        except:
            print("unable to open video")
            print(format_exc())
            self.haserror.value = True
            self.isdone.value = True
            return
        
        try:
            if length > MAX_FRAMES_RENDER:
                length = MAX_FRAMES_RENDER
            
            self.totalframes.value = length
            
            # Get width and height of video stream
            w = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))

            for frame_num in range(length):
                ret, frame = cap.read()
                if not ret:
                    # return with error
                    self.haserror.value = True
                    break
                
                if frame_num == 0:
                    # do first frame stuff
                    prev_frame = frame
                    prev_gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
                    prev_pts = cv.goodFeaturesToTrack(prev_gray,
                                                maxCorners=200,
                                                qualityLevel=0.01,
                                                minDistance=30.0,
                                                blockSize=3)

                    prev_thresh = np.zeros((h,w),dtype=np.uint8)
                    prev_thresh_sub = prev_thresh
                    prev2_thresh = prev_thresh
                    prev2_thres_sub = prev_thresh

                    background = cv.cvtColor(frame, cv.COLOR_BGR2BGRA)
                    alpha_background = background[:,:,3] / 255.0
                    
                    # skip everything and go to next frame
                    continue

                if frame_num % self.skip_frames != 0:
                    # just skip it
                    continue
                
                # frames are zero indexed duh
                self.currframe.value = frame_num + 1
                
                curr_gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY) 

                curr_pts, status, err = cv.calcOpticalFlowPyrLK(prev_gray, curr_gray, prev_pts, None) 
                
                # Filter only valid points
                idx = np.where(status==1)[0]
                prev_pts = prev_pts[idx]
                curr_pts = curr_pts[idx]
                
                #Find transformation matrix            
                m, ret = cv.estimateAffinePartial2D(np.array(curr_pts), np.array(prev_pts))

                # Extract traslation
                dx = m[0,2]
                dy = m[1,2]
                
                # Extract rotation angle
                da = np.arctan2(m[1,0], m[0,0])

                m = np.zeros((2,3), np.float32)
                m[0,0] = np.cos(da)
                m[0,1] = -np.sin(da)
                m[1,0] = np.sin(da)
                m[1,1] = np.cos(da)
                m[0,2] = dx
                m[1,2] = dy

                # Apply affine wrapping to the given frame
                frame_stabilized = cv.warpAffine(frame, m, (w,h))

                # calculate difference
                diff = cv.absdiff(frame_stabilized,prev_frame)
                ret,thresh = cv.threshold(diff,50,255,cv.THRESH_BINARY)
                thresh = cv.cvtColor(thresh, cv.COLOR_BGR2GRAY)

                # subtract previous mask from this one
                thresh_sub = cv.subtract(thresh,prev_thresh)
                thresh_sub = cv.subtract(thresh_sub,prev2_thresh) 

                # set the mask as the alpha
                foreground = cv.cvtColor(frame_stabilized, cv.COLOR_BGR2BGRA)
                foreground[:,:,3] = thresh_sub

                alpha_foreground = foreground[:,:,3] / 255.0

                # set adjusted colors
                for color in range(0, 3):
                    background[:,:,color] = alpha_foreground * foreground[:,:,color] + \
                        alpha_background * background[:,:,color] * (1 - alpha_foreground)

                # set adjusted alpha and denormalize back to 0-255
                background[:,:,3] = (1 - (1 - alpha_foreground) * (1 - alpha_background)) * 255

                
                # do last stuff

                #save curent values as prevs
                prev_frame = frame_stabilized
                prev_gray = cv.cvtColor(prev_frame,cv.COLOR_BGR2GRAY)
                prev_pts = cv.goodFeaturesToTrack(prev_gray,
                                                maxCorners=200,
                                                qualityLevel=0.01,
                                                minDistance=30.0,
                                                blockSize=3)
                prev2_thresh = prev_thresh
                prev2_thres_sub = prev_thresh_sub
                prev_thresh = thresh
                prev_thresh_sub = thresh_sub

                # only show the opencv window if this mode is on.
                if DEBUG_CV_IMSHOW:
                    cv.imshow('frame',background)
                    frame_num += 1
                    if cv.waitKey(1) & 0xFF == ord('q'):
                        break
                    elif cv.waitKey(1) & 0xFF == ord('w'):
                        time.sleep(5)
                
                # save to the out image
                cv.imwrite(self.imgpath,background)
        
        except Exception as e:
            print("Error generating image")
            print(format_exc())
            self.haserror.value = True
        
        if DEBUG_CV_IMSHOW:
            cv.destroyAllWindows()
        
        cap.release()
        self.isdone.value = True

        return


def getInputFile(folderpath):
    for fname in os.listdir(folderpath):
        if "in." in fname:
            #return(f'{folderpath}/{fname}')
            return(fname)
    return(None)

# TEST PROGRAM
if __name__ == "__main__":
    m = bgenManager()

    folder1 = "/Users/nmass/Software/birdflight/birdflight/app/static/user/710f861f-a838-4546-8123-458ed89496b9"
    folder2 = "/Users/nmass/Software/birdflight/birdflight/app/static/user/c9344ae2-1b75-4ec7-8a9a-64d8141efc8c"

    m.startWorker("asdklfjaslkdfj",folder1,5,0)

    for i in range(5):
        time.sleep(1)
        print(m.allWorkers)

    m.startWorker("sadfs2222222",folder2,5,10)
    
    for i in range(20):
        time.sleep(1)
        print(m.allWorkers)

    m.cullWorkers()

    print(m.allWorkers)

