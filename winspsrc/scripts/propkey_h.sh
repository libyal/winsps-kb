#!/bin/bash
#
# Script to extract property descriptions from the propkey.h header file.

EXIT_SUCCESS=0;
EXIT_FAILURE=1;

FILENAME=$1;
BASENAME=`basename ${FILENAME}`;

set -e;

mkdir -p build

cat ${FILENAME} | grep 'DEFINE_PROPERTYKEY(' | sed 's/^.*DEFINE_PROPERTYKEY(//;s/, 0[xX]\(........\), 0[xX]\(....\), 0[xX]\(....\), 0[xX]\(..\), 0[xX]\(..\), 0[xX]\(..\), 0[xX]\(..\), 0[xX]\(..\), 0[xX]\(..\)/\t\L\1-\L\2-\L\3-\L\4\L\5-\L\6\L\7\L\8\L\9/;s/, 0[xX]\(..\), 0[xX]\(..\), \(.*\));/\L\1\L\2\t\L\3/;s/\r$//' | grep -v 'name, l, w1, w2, b1, b2, b3, b4, b5, b6, b7, b8, pid' | sed 's/\([^\t]*\)\t\([^\t]*\)\t\([^\s]*\)$/---\nshell_property_key: \1\nformat_identifier: \2\nproperty_identifier: \3/' > build/${BASENAME}.yaml;

exit ${EXIT_SUCCESS};

