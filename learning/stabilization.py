import cv2 as cv
import numpy as np
import vidstab

import imutils.feature.factories as kp_factory


#cap = cv.VideoCapture('20241216_143841.mp4')
cap = cv.VideoCapture('20241216_142253.mp4')

length = int(cap.get(cv.CAP_PROP_FRAME_COUNT))


print(length)

if False:
    # Using defaults
    cap.release()
    stabilizer = vidstab.VidStab()
    stabilizer.stabilize(input_path='20241216_143841.mp4', 
                        output_path='stab3.avi',
                        smoothing_window=110,
                        border_size=10,
                        layer_func=vidstab.layer_overlay)

    exit()



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
    
    #save curent values as prevs
    prev_frame = frame_stabilized
    prev_gray = cv.cvtColor(prev_frame,cv.COLOR_BGR2GRAY)
    prev_pts = cv.goodFeaturesToTrack(prev_gray,
                                    maxCorners=200,
                                    qualityLevel=0.01,
                                    minDistance=30.0,
                                    blockSize=3)



    cv.imshow('frame',frame_stabilized)
    frame_num += 1
    if cv.waitKey(1) & 0xFF == ord('q'):
        break




cv.destroyAllWindows()