#!/usr/bin/env bash

tvservice -p
#tvservice --explicit="CEA 16 HDMI"   # sets the TV to 1080p
fbset -depth 8
fbset -g 1920 1080 1920 1080 16
