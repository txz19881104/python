#!/bin/sh

log_time=`date "+%G-%m-%d %H:%M:%S"`
log_time=$log_time".log"
python3 api.py Fiction UpdateChapter > /home/txz/Entertainment/log/$log_time 2>&1
