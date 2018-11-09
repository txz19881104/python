#!/bin/sh

cd /home/txz/Entertainment/spider
export LC_ALL=zh_CN.UTF-8
log_time=`date "+%G-%m-%d %H:%M:%S"`
log_time=$log_time".log"
python3 api.py Comic UpdateChapter > /home/txz/Entertainment/log/comic/$log_time 2>&1
