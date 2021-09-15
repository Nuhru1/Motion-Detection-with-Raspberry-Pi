# Motion detection with the Raspberry Pi, OpenCV, and Dropbox

In this project if the raspberry camera detect a motion, it will first capture and store the picture locally in a temporary file and then send the picture into dropbox. After sending sending the picture into dropbox it will delete the temporary file.

For that we need our dropbox_access_token, that can be find in the following link:
https://www.dropbox.com/developers

The pyimagesearch package contain the tempimage module which will allow us to store the image locally before sending into our dropbox. This package can be found in https://www.pyimagesearch.com
