# ofunctions
## Collection of useful python functions

[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![Percentage of issues still open](http://isitmaintained.com/badge/open/netinvent/ofunctions.svg)](http://isitmaintained.com/project/netinvent/ofunctions "Percentage of issues still open")
![Linux Build Status](https://github.com/netinvent/ofunctions/workflows/ofunctions-linux-tests/badge.svg)
[![GitHub Release](https://img.shields.io/github/release/netinvent/ofunctions.svg?label=Latest)](https://github.com/netinvent/ofunctions/releases/latest)

ofunctions is a set of various recurrent functions amongst

- bisection: bisection algorithm for *any* function with *any* number of arguments, works LtoR and RtoL
- checksums: various SHA256 tools for checking and creating checksum files
- csv: CSV file reader with various enhancements over generic reader
- delayed_keyboardinterrupt: just a nifty tool to catch CTRL+C signals
- file_utils: file handling functions of which get_files_recursive is the most advanced
- json_sanitize: make sure json does not contain unsupported chars, yes I look at you Windows eventlog
- logger_utils: basic no brain console + file log creation
- mailer: send emails regardless of ssl/tls protocols, in batch or as single mail, with attachments
- network: various tools like ping, internet check, MTU probing and public IP discovery
- platform: nothing special here, just check what arch we are running on
- process: simple kill-them-all function to terminate subprocesses
- random: basic random string & password generator
- service_control: control Windows / Linux service start / stop / status
- string_handling: remove accents / special chars from strings
- threading: threading decorator for functions

## Setup

```
pip install ofunctions.<subpackage>

```
