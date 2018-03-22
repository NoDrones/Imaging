# Face Detection Example
#
# This example shows off the built-in face detection feature of the OpenMV Cam.
#
# Face detection works by using the Haar Cascade feature detector on an image. A
# Haar Cascade is a series of simple area contrasts checks. For the built-in
# frontalface detector there are 25 stages of checks with each stage having
# hundreds of checks a piece. Haar Cascades run fast because later stages are
# only evaluated if previous stages pass. Additionally, your OpenMV Cam uses
# a data structure called the integral image to quickly execute each area
# contrast check in constant time (the reason for feature detection being
# grayscale only is because of the space requirment for the integral image).

import sensor, time, image

# Reset sensor
sensor.reset()

# Sensor settings
sensor.set_contrast(3)
sensor.set_gainceiling(16)
# HQVGA and GRAYSCALE are the best for face tracking.
sensor.set_framesize(sensor.VGA)
sensor.set_windowing((240, 160))
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_auto_gain(True)
sensor.set_auto_exposure(False, value = 30)


# Skip a few frames to allow the sensor settle down
sensor.skip_frames(time = 2000)



# Load Haar Cascade
# By default this will use all stages, lower satges is faster but less accurate.
beetle_cascade = image.HaarCascade("./potato_beetle0.cascade", stages=20)

# FPS clock
clock = time.clock()

while (True):
    clock.tick()

    # Capture snapshot
    img = sensor.snapshot()

    # Find objects.
    # Note: Lower scale factor scales-down the image more and detects smaller objects.
    # Higher threshold results in a higher detection rate, with more false positives.
    objects = img.find_features(beetle_cascade, threshold=0.5, scale_factor=1.1)

    # Draw objects
    for r in objects:
        img.draw_rectangle(r, color = 120)

    # Print FPS.
    # Note: Actual FPS is higher, streaming the FB makes it slower.
    print(clock.fps())
