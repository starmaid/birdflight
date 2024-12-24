import cv2 as cv
import numpy as np
import time

#cap = cv.VideoCapture('osprey_slomo.mp4')
cap = cv.VideoCapture('20241216_142253.mp4')

do_stabilize = True

ret, frame1 = cap.read()
frame_prev = frame1
frame = None
background = cv.cvtColor(frame1, cv.COLOR_BGR2BGRA)
alpha_background = background[:,:,3] / 255.0

# Get width and height of video stream
w = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))

frame_num = 0

while(cap.isOpened()):
    frame_num += 1

    ret, frame = cap.read()
    if not frame_num % 4 == 0:
        continue

    if do_stabilize:
        # do the image stabilization
        prev_gray = cv.cvtColor(frame_prev, cv.COLOR_BGR2GRAY)
        prev_pts = cv.goodFeaturesToTrack(prev_gray,
                                        maxCorners=200,
                                        qualityLevel=0.01,
                                        minDistance=30,
                                        blockSize=3)

        
        curr_gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY) 

        curr_pts, status, err = cv.calcOpticalFlowPyrLK(prev_gray, curr_gray, prev_pts, None) 
        # Filter only valid points
            
        idx = np.where(status==1)[0]
        prev_pts = prev_pts[idx]
        curr_pts = curr_pts[idx]
        
        #Find transformation matrix
        m, ret = cv.estimateAffinePartial2D(curr_pts,prev_pts)

        #print(ret)
        
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
        frame = frame_stabilized




    # calculate difference
    
    diff = cv.absdiff(frame,frame_prev)
    ret,thresh = cv.threshold(diff,40,255,cv.THRESH_BINARY)
    thresh = cv.cvtColor(thresh, cv.COLOR_BGR2GRAY)

    # floodfil the threshold
    #h, w = thresh.shape[:2]
    #mask = np.zeros((h+2, w+2), np.uint8)
    #flood = thresh.copy()
    #ret = cv.floodFill(thresh, mask,(0,0), 255)

    
    foreground = cv.cvtColor(frame, cv.COLOR_BGR2BGRA)
    foreground[:,:,3] = thresh

    # normalize alpha channels from 0-255 to 0-1
    
    alpha_foreground = foreground[:,:,3] / 255.0

    # set adjusted colors
    for color in range(0, 3):
        background[:,:,color] = alpha_foreground * foreground[:,:,color] + \
            alpha_background * background[:,:,color] * (1 - alpha_foreground)

    # set adjusted alpha and denormalize back to 0-255
    background[:,:,3] = (1 - (1 - alpha_foreground) * (1 - alpha_background)) * 255

    

    cv.imshow('frame',background)
    frame_prev = frame
    if cv.waitKey(1) & 0xFF == ord('q'):
        break




#threshold(diff, thresh, 0, 255, THRESH_BINARY_INV | THRESH_OTSU);


class thing:
    a = 4
    def something(self):
        self.a += 1