#!/bin/bash
#
# Script to extract property descriptions from the propkey.h header file.

EXIT_SUCCESS=0;
EXIT_FAILURE=1;

FILENAME=$1;
BASENAME=`basename ${FILENAME}`;

set -e;

mkdir -p build

sed -n '/<summary>/,/<\/summary>/ { /<para>Name:/ { s/^.*<para>Name:\s\s*\(.*\) -- \(.*\)<\/para>/\1\t\2/; p }; /<para>Type:/ { s/^.*<para>Type:\s\s*.* -- \([^(]*\).*<\/para>/\1/; p }; /<para>FormatID:/ { s/^.*<para>FormatID:\s\s*\(.*\)[{]\(.*\)[}], \([0-9][0-9]*\)\(.*\)<\/para>/\2\t\3\t\1\t\4/; p } }' ${FILENAME} | sed 'N;N;s/\n/\t/g' | sed 's/\([^\t]*\)\t\([^\t]*\)\t\([^\t]*\)\t\([^\t]*\)\t\([^\t]*\)\t\([^\t]*\)\t\([^\t]*\)$/---\nname: \1\nshell_property_key: \2\nformat_identifier: \4\nformat_class: \6\nproperty_identifier: \5\nalias: \7\nvalue_type: \3/' > build/${BASENAME}.yaml;

sed 's/^format_identifier: \(.*\)$/format_identifier: \L\1/' -i build/${BASENAME}.yaml;

sed 's/^format_class:\s\s*(\(\S[^ )]*\).*/format_class: \1/' -i build/${BASENAME}.yaml;
sed '/^format_class:\s\s*$/ d' -i build/${BASENAME}.yaml;

sed 's/^alias:\s\s*(\(\S[^ )]*\).*/alias: \1/' -i build/${BASENAME}.yaml;
sed '/^alias:\s\s*[^_]*$/ d' -i build/${BASENAME}.yaml;

exit ${EXIT_SUCCESS};

