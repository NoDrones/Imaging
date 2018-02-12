General information about the openmvcam
=======================================

.. contents::

Local filesystem and SD card
----------------------------

There is a small internal filesystem (a drive) on the openmvcam which is stored within the microcontroller's flash memory.

When the openmvcam boots up, it needs to choose a filesystem to boot from.  If
there is no SD card, then it uses the internal filesystem as the boot
filesystem, otherwise, it uses the SD card.  After the boot, the current
directory is set to ``/``.

The boot filesystem is used for 2 things: it is the filesystem from which
the ``main.py`` files are searched for, and it is the filesystem
which is made available on your PC over the USB cable.

The filesystem will be available as a USB flash drive on your PC.  You can
save files to the drive, and edit ``main.py``.

*Remember to eject (on Linux, unmount) the USB drive before you reset your
pyboard.*

Boot modes
----------

On powerup, if powered by USB, the OpenMV Cam will run a bootloader program for
about 3 seconds which allows OpenMV IDE to update the firmware without using DFU.  After
3 seconds then bootloader will exit and then ``main.py`` will run.  If not powered
by USB then ``main.py`` will run immediantly.

Flashing LED Errors
-------------------

If all colors of the RGB LED are flashing quickly there was a hard fault.  Reflash
your OpenMV Cam's firmware to fix this issue.  If this does not work your OpenMV Cam
may be damaged...
