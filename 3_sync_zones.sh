#!/bin/bash

if [ -z $1 ]; then
	mask="*.zone"
else
	mask=$*
fi
for z in zones/$mask; do
	if [ "zones/$mask" == "$z" ]; then
		echo "No zone found for \"$mask\""
	else
		echo $z
		./route53zone.py sync_zonefile $z alias.map log/${z#zones/}.log
	fi
done
