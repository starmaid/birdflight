import cv2 as cv
import numpy as np

import time

import imutils.feature.factories as kp_factory

#cap = cv.VideoCapture('../test_video/osprey_slomo.mp4')
#cap = cv.VideoCapture('../test_video/20241216_143841.mp4')
cap = cv.VideoCapture('test_video/20241216_142253.mp4')

length = int(cap.get(cv.CAP_PROP_FRAME_COUNT))


print(length)


# Get width and height of video stream
w = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))

frame_num = 0

raw_frames = []
transforms = [None]

# loop one: calculate transforms

while(cap.isOpened()):
    ret, frame = cap.read()
    if not ret:
        break
    if frame_num == 0:
        prev_frame = frame
        prev_gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        prev_pts = cv.goodFeaturesToTrack(prev_gray,
                                    maxCorners=200,
                                    qualityLevel=0.01,
                                    minDistance=30.0,
                                    blockSize=3)
        raw_frames.append(frame)

        prev_thresh = np.zeros((h,w),dtype=np.uint8)
        prev_thresh_sub = prev_thresh
        prev2_thresh = prev_thresh
        prev2_thres_sub = prev_thresh

        background = cv.cvtColor(frame, cv.COLOR_BGR2BGRA)
        alpha_background = background[:,:,3] / 255.0

        frame_num += 1
        continue

    if frame_num %1 != 0:
        frame_num += 1
        continue
    curr_gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY) 
    raw_frames.append(frame)

    curr_pts, status, err = cv.calcOpticalFlowPyrLK(prev_gray, curr_gray, prev_pts, None) 
    
    # Filter only valid points
    idx = np.where(status==1)[0]
    prev_pts = prev_pts[idx]
    curr_pts = curr_pts[idx]
    
    #Find transformation matrix
    #m, ret = cv.estimateAffine2D(prev_pts, curr_pts)
    
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

    transforms.append(m)

    # Apply affine wrapping to the given frame
    frame_stabilized = cv.warpAffine(frame, m, (w,h))
    

    # calculate difference
    
    diff = cv.absdiff(frame_stabilized,prev_frame)
    ret,thresh = cv.threshold(diff,50,255,cv.THRESH_BINARY)
    thresh = cv.cvtColor(thresh, cv.COLOR_BGR2GRAY)

    # subtract previous mask from this one
    thresh_sub = cv.subtract(thresh,prev_thresh)
    #prev2_thresh_box = cv.boxFilter(prev2_thresh,-1,(5,5),normalize=True) # this is blurring, i would rather extend it
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

    testlayer = np.ndarray((h,w,3),dtype=np.uint8)

    testlayer[:,:,0] = thresh_sub
    #testlayer[:,:,1] = prev_thresh
    #testlayer[:,:,2] = prev2_thresh
    


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

    cv.imshow('frame',background)
    frame_num += 1
    if cv.waitKey(1) & 0xFF == ord('q'):
        break
    elif cv.waitKey(1) & 0xFF == ord('w'):
        time.sleep(5)

cv.imwrite(f"output/save_{time.time()}.png",background)

cv.destroyAllWindows()