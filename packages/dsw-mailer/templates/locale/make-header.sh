#!/usr/bin/env bash

TS=$(date -z"UTC" +"%Y-%m-%dT%H:%M:%SZ")
NL='\n'

echo "#Comment for updating this file"
echo "msgid \"\""
echo "msgstr \"\""
echo "\"Project-Id-Version: $1\\n\""
echo "\"POT-Creation-Date: $TS\\n\""
echo "\"Language: en\\n\""
echo "\"Content-Type: text/plain; charset=UTF-8\\n\""
echo "\"Content-Transfer-Encoding: 8bit\\n\""
echo "\"Plural-Forms: nplurals=2; plural=n == 1 ? 0 : 1;\\n\""
echo ""
cat $2
