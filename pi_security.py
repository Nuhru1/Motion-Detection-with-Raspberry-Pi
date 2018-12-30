from pyimagesearch.tempimage import TempImage
from picamera.array import PiRGBArray
from picamera import PiCamera
import dropbox
import cv2
import datetime
import json
import warnings
import time

# filter warnings, load the configuration and initialize the Dropbox
# client
warnings.filterwarnings("ignore")
json_file = json.load(open('conf1.json'))
client = None

# check to see if the Dropbox should be used
if json_file["use_dropbox"]:
    # connect to dropbox and start the session authorization process
    client = dropbox.Dropbox(json_file["dropbox_access_token"])
    print("[SUCCESS] dropbox account linked")
    
# initialize the camera and grab a reference to the raw camera capture
camera = PiCamera()
camera.resolution = tuple(json_file["resolution"])
camera.framerate = json_file["fps"]
rawCapture = PiRGBArray(camera, size=tuple(json_file["resolution"]))

# allow the camera to warmup, then initialize the average frame, last
# uploaded timestamp, and frame motion counter
print("[INFO] warming up...")
time.sleep(json_file["camera_warmup_time"])
avg = None
lastUploaded = datetime.datetime.now()
motionCounter = 0

# capture frames from the camera
for f in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
    # grab the raw NumPy array representing the image and initialize
    # the timestamp and occupied/unoccupied text
    frame = f.array
    timestamp = datetime.datetime.now()
    text = 'Unocupied'
    # resize the frame, convert it to grayscale, and blur it
    frame = cv2.resize(frame, (500,300))
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    # if the average frame is None, initialize it
    if avg is None:
        print("[INFO] starting background model...")
        avg = gray.copy().astype("float")
        rawCapture.truncate(0)
        continue
    # accumulate the weighted average between the current frame and
    # previous frames, then compute the difference between the current
    # frame and running average    
    cv2.accumulateWeighted(gray, avg, 0.5)
    frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))
    
    # threshold the delta image, dilate the thresholded image to fill
    # in holes, then find contours on thresholded image
    thresh = cv2.threshold(frameDelta, json_file["delta_thresh"], 255,cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    (_,cnts,_) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

    # loop over the contours
    for c in cnts:
        # if the contour is too small, ignore it
        if cv2.contourArea(c) < json_file["min_area"]:
            continue
            
            # compute the bounding box for the contour, draw it on the frame, and update the text
        (x, y, w, h) = cv2.boundingRect(c)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        text = "Occupied"

    # draw the text and timestamp on the frame
    ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
    cv2.putText(frame, "Room Status: {}".format(text), (10, 20),cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX,0.35, (0, 0, 255), 1)

    # check to see if the room is occupied
    if text == "Occupied":
	# check to see if enough time has passed between uploads
        if (timestamp - lastUploaded).seconds >=json_file["min_upload_seconds"]:
        # increment the motion counter
            motionCounter += 1
            

	    # check to see if the number of frames with consistent motion is
	    # high enough

            if motionCounter >=json_file["min_motion_frames"]:
		# check to see if dropbox sohuld be used
                if json_file["use_dropbox"]:
		    # write the image to temporary file
                    t = TempImage()
                    cv2.imwrite(t.path, frame)
		    # upload the image to Dropbox and cleanup the tempory image
                    print("[UPLOAD] {}".format(ts))
                    path = "/{base_path}/{timestamp}.jpg".format(base_path=json_file["dropbox_base_path"], timestamp=ts)
                    client.files_upload(open(t.path, "rb").read(), path)
                t.cleanup()

                # update the last uploaded timestamp and reset the motion
		# counter
                lastUploaded = timestamp
                motionCounter = 0
                
                
    # otherwise, the room is not occupied
    else:
        motionCounter = 0
        
    if json_file["show_video"]:
        cv2.imshow("Security Feed", frame)
        key = cv2.waitKey(1) & 0xFF

        # if the `q` key is pressed, break from the loop
        if key == ord("q"):
            break
    # clear the stream in preparation for the next frame      
    rawCapture.truncate(0)
      
