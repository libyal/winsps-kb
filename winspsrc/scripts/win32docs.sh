#!/bin/bash
#
# Script to extract property descriptions from public Microsoft Win32
# documentation.
# Requires Linux with git

EXIT_SUCCESS=0;
EXIT_FAILURE=1;

# Checks the availability of a binary and exits if not available.
#
# Arguments:
#   a string containing the name of the binary
#
assert_availability_binary()
{
	local BINARY=$1;

	which ${BINARY} > /dev/null 2>&1;
	if test $? -ne ${EXIT_SUCCESS};
	then
		echo "Missing binary: ${BINARY}";
		echo "";

		exit ${EXIT_FAILURE};
	fi
}

assert_availability_binary git;

set -e;

mkdir -p build

git clone https://github.com/MicrosoftDocs/win32.git

(cd win32 && grep -h -re 'propertyDescription$' -A 4 desktop-src/properties/* | grep -A3 'name = ' | sed 's/   name = /name: /;s/   shellPKey = /shell_property_key: /;s/   formatID = \(.*\)/format_identifier: \L\1/;s/   propID = /property_identifier: /;s/--/---/' > ../build/win32docs.yaml)

rm -rf win32;

exit ${EXIT_SUCCESS};

