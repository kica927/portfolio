#!/usr/bin/env bash
S=/home/lemma/so101_ws/src/so101_gazebo/scripts/run_sim_test.sh
C=/home/lemma/so101_ws/src/so101_gazebo/config
R=/home/lemma/so101_ws/results
CHAIN=gravity_compensation,arm_controller
: > $R/grpB.log
$S effort hold_after 91 "" _s10 $C/controllers_effort_1k_gc.yaml $CHAIN 1.0 >> $R/grpB.log 2>&1
$S effort hold_after 92 "" _s09 $C/controllers_effort_1k_gc_s09.yaml $CHAIN 0.9 >> $R/grpB.log 2>&1
$S effort hold_after 93 "" _s00 $C/controllers_effort_1k_gc_s00.yaml $CHAIN 0.0 >> $R/grpB.log 2>&1
grep -v -E "pal_statistics|Waiting RM|statistics initialized|Executor is not available|update period|평균 오차|RMS 오차|최대 \|오차\||최대 \|출력\||최대 \|속도\||\[전체\]|\[정상상태_A\]|shoulder_pan  shoulder_lift     elbow_flex     wrist_flex     wrist_roll$" $R/grpB.log | grep -v "^\s*$"
