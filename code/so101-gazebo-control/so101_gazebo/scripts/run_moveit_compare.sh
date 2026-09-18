#!/usr/bin/env bash
S=/home/lemma/so101_ws/src/so101_gazebo/scripts/run_sim_test.sh
C=/home/lemma/so101_ws/src/so101_gazebo/config
R=/home/lemma/so101_ws/results
: > $R/moveit_compare.log
$S effort moveit 131 "" _pd $C/controllers_effort_1k.yaml >> $R/moveit_compare.log 2>&1
$S effort moveit 132 "" _ff_full $C/controllers_effort_1k_ff_full.yaml gravity_compensation,arm_controller >> $R/moveit_compare.log 2>&1
grep -v -E 'pal_statistics|Waiting RM|statistics initialized|Executor is not available|update period|평균 오차' $R/moveit_compare.log | grep -v '^\s*$'
