#!/bin/sh
# This script will recreate all the "gold standard" output files based on
# a run of the existing software. DO NOT RUN THIS UNLESS YOU ARE WILLING
# TO MANUALLY INSPECT ALL OUTPUT FILES AFTER EXECUTION. FAILING TO DO SO
# WILL MAKE THE RELEVANT TESTS USELESS.

for sample in sample_*.py;do
	case $sample in
		*.out*.py)	:;;
		*)	sampleBase=`basename -s .py $sample`
			echo "Processing" $sampleBase
			../doxypypy.py --autocode --autobrief --ns=$sampleBase $sample > $sampleBase.out.py
			../doxypypy.py --autocode --autobrief $sample > $sampleBase.outnn.py
			../doxypypy.py --autobrief --ns=$sampleBase $sample > $sampleBase.outnc.py
			../doxypypy.py $sample > $sampleBase.outbare.py
	esac
done

echo "Processing complete."
echo
echo "Now you must visually inspect each output file and verify that"
echo "it will properly serve as a new gold standard for future"
echo "comparisons. Failing to do so will make all the comparison"
echo "tests a waste of time."

