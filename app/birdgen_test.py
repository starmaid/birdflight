import cv2 as cv
import numpy as np
from multiprocessing import Process, shared_memory, Value, Array, Queue
from ctypes import Structure, c_int32, c_bool, c_char_p
import time
from traceback import format_exc

from birdgen import *


def test4():
    folder1 = "../test_video"
    img_tweak_params = {
        "frame_diff_threshold": 50,
        "background_diff_threshold": 250,
        "denoise_radius": 4,
    }
    w = bgenWorker(
        Value(c_bool, False),
        Value(c_bool, False),
        Value(c_int32, 0),
        Value(c_int32, 0),
        Array("c", SHARED_STRING_LEN),
        Array("c", SHARED_STRING_LEN),
        folder1,
        getInputFile(folder1),
        Queue(),
    )
    w.setParams(4, img_tweak_params)
    
    w.openfile()
    w.stabilized_frames = np.load("stabilized_bird_10.npy")
    w.getAverageFrame()
    w.layering()


def test3():
    folder1 = "../test_video"
    img_tweak_params = {
        "frame_diff_threshold": 50,
        "background_diff_threshold": 50,
        "denoise_radius": 4,
    }
    w = bgenWorker(
        Value(c_bool, False),
        Value(c_bool, False),
        Value(c_int32, 0),
        Value(c_int32, 0),
        Array("c", SHARED_STRING_LEN),
        Array("c", SHARED_STRING_LEN),
        folder1,
        getInputFile(folder1),
        Queue(),
    )
    w.setParams(10, {})
    
    w.openfile()
    w.stabilized_frames = np.load("stabilized_bird_10.npy")
    w.getAverageFrame()

    while True:
        cv.imshow("frame", w._background)
        if cv.waitKey(1) & 0xFF == ord("q"):
            break
        elif cv.waitKey(1) & 0xFF == ord("w"):
            time.sleep(5)
        time.sleep(0.1)

    cv.destroyAllWindows()


def test2():
    folder1 = "../test_video"
    w = bgenWorker(
        Value(c_bool, False),
        Value(c_bool, False),
        Value(c_int32, 0),
        Value(c_int32, 0),
        Array("c", SHARED_STRING_LEN),
        Array("c", SHARED_STRING_LEN),
        folder1,
        getInputFile(folder1),
        Queue(),
    )
    w.setParams(10, {})
    
    w.openfile()
    # print("file opened")
    w.stabilize()
    print("Stabilized")

    np.save("stabilized_bird_10", w.stabilized_frames)
    return
    w.stabilized_frames = np.load("stabilized_zach.npy")
    f = w.getAverageFrame()

    while True:
        cv.imshow("frame", f)
        if cv.waitKey(1) & 0xFF == ord("q"):
            break
        elif cv.waitKey(1) & 0xFF == ord("w"):
            time.sleep(5)
        time.sleep(0.1)

    cv.destroyAllWindows()


def test1():
    m = bgenManager()

    folder1 = "../test_video"
    # folder2 = "/Users/nmass/Software/birdflight/birdflight/app/static/user/c9344ae2-1b75-4ec7-8a9a-64d8141efc8c"

    m.startWorker("asdklfjaslkdfj", folder1)

    for i in range(10):
        time.sleep(1)
        print(m.allWorkers)

    # m.startWorker("sadfs2222222",folder2,5,10)

    # for i in range(20):
    #    time.sleep(1)
    #    print(m.allWorkers)

    m.cullWorkers()

    print(m.allWorkers)


# TEST PROGRAM
if __name__ == "__main__":
    test4()
