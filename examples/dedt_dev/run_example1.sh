#!/usr/bin/env bash

# define command with arguments
cmd="time python dedt_dev.py -c 0 -n a,b,c --EOT 4 -f ./testFiles/example1.ded --evaluator c4"

# run command an do not hide stdout
$cmd
