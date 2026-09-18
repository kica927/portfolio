#!/usr/bin/env bash
S=/home/lemma/so101_ws/src/so101_gazebo/scripts/run_sim_test.sh
C=/home/lemma/so101_ws/src/so101_gazebo/config
R=/home/lemma/so101_ws/results
CHAIN=gravity_compensation,arm_controller
sed 's/    scale: 1.0/    scale: 1.0\n    feedforward: nle/' $C/controllers_effort_1k_gc.yaml > $C/controllers_effort_1k_ff_nle.yaml
sed 's/    scale: 1.0/    scale: 1.0\n    feedforward: full/' $C/controllers_effort_1k_gc.yaml > $C/controllers_effort_1k_ff_full.yaml
grep -H feedforward $C/controllers_effort_1k_ff_*.yaml
: > $R/feedforward.log
$S effort step 121 "" _B_ff_gravity $C/controllers_effort_1k_gc.yaml $CHAIN >> $R/feedforward.log 2>&1
$S effort step 122 "" _B_ff_nle $C/controllers_effort_1k_ff_nle.yaml $CHAIN >> $R/feedforward.log 2>&1
$S effort step 123 "" _B_ff_full $C/controllers_effort_1k_ff_full.yaml $CHAIN >> $R/feedforward.log 2>&1
grep -v -E "pal_statistics|Waiting RM|statistics initialized|Executor is not available|update period|평균 오차|최대 \|출력\|" $R/feedforward.log | grep -v "^\s*$"
