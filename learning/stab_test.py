import cv2 as cv
import numpy as np
import vidstab
import time

#cap = cv.VideoCapture('20241216_143841.mp4')
cap = cv.VideoCapture('20241216_142253.mp4')

# Get width and height of video stream
w = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))

frame_num = 0

raw_frames = []
transforms = [None]

# loop one: calculate transforms

# frame 1
ret, frame = cap.read()

prev_frame = frame
prev_gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
prev_pts = cv.goodFeaturesToTrack(prev_gray,
                            maxCorners=200,
                            qualityLevel=0.01,
                            minDistance=30.0,
                            blockSize=3)

raw_frames.append(frame)
frame_num += 1




# frame 2
for i in range(10):
    ret, frame = cap.read()




curr_gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY) 
raw_frames.append(frame)

curr_pts, status, err = cv.calcOpticalFlowPyrLK(prev_gray, curr_gray, prev_pts, None) 

# Filter only valid points
idx = np.where(status==1)[0]
prev_pts = prev_pts[idx]
curr_pts = curr_pts[idx]


prev_pts2 = np.intp(prev_pts)
copy = np.array(prev_frame)
for i in prev_pts2:
    x,y = i.ravel()
    cv.circle(copy,(x,y),3,(0,255,0),-1)

prev_pts3 = np.intp(curr_pts)
copy2 = np.array(frame)
for i in prev_pts3:
    x,y = i.ravel()
    cv.circle(copy2,(x,y),3,(255,0,0),-1)

f = cv.addWeighted(copy,0.8, copy2, 0.2,0)

while True:
    cv.imshow("frame", f)
    if cv.waitKey(1) & 0xFF == ord('q'):
        break



#Find transformation matrix
#m, ret = cv.estimateAffine2D(prev_pts, curr_pts)

transform, ret = cv.estimateAffinePartial2D(np.array(curr_pts),np.array(prev_pts))

# extract v2 
dx = transform[0, 2]
# translation y
dy = transform[1, 2]
# rotation
da = np.arctan2(transform[1, 0], transform[0, 0])

transform = [dx,dy,da]

transform_matrix = np.zeros((2, 3))

transform_matrix[0, 0] = np.cos(transform[2])
transform_matrix[0, 1] = -np.sin(transform[2])
transform_matrix[1, 0] = np.sin(transform[2])
transform_matrix[1, 1] = np.cos(transform[2])
transform_matrix[0, 2] = transform[0]
transform_matrix[1, 2] = transform[1]

m = transform_matrix

if False:
    m = transform
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
h, w = frame.shape[:2]
frame_stabilized = cv.warpAffine(frame, m, (w,h))


f = cv.addWeighted(copy,0.8, frame_stabilized, 0.2,0)

while True:
    cv.imshow("frame", f)
    if cv.waitKey(1) & 0xFF == ord('q'):
        break

quit()




#save curent values as prevs
prev_frame = frame_stabilized
prev_gray = cv.cvtColor(prev_frame,cv.COLOR_BGR2GRAY)
prev_pts = cv.goodFeaturesToTrack(prev_gray,
                                maxCorners=200,
                                qualityLevel=0.01,
                                minDistance=30.0,
                                blockSize=3)


prev_pts2 = np.intp(prev_pts)

copy = np.array(prev_gray)

for i in prev_pts2:
    x,y = i.ravel()
    cv.circle(copy,(x,y),3,255,-1)

cv.imshow('frame',copy)
frame_num += 1




cv.destroyAllWindows()