#!/usr/bin/env bash
S=/home/lemma/so101_ws/src/so101_gazebo/scripts/run_sim_test.sh
C=/home/lemma/so101_ws/src/so101_gazebo/config
R=/home/lemma/so101_ws/results
: > $R/switch_repeat.log
for i in 1 2 3 4 5; do
  $S effort hold_after $((93 + i)) "" _switch$i $C/controllers_effort_1k_gc.yaml gravity_compensation,arm_controller 1.0 >> $R/switch_repeat.log 2>&1
done
grep -E "^== \[effort_hold_after_switch|킥|전환 ±5ms|^\s+[+-][0-9]+\.[0-9] \||전환 시각 기준" $R/switch_repeat.log
