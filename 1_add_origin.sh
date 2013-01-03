#!/bin/bash

for z in zones/*.zone; do
	if ! grep '$ORIGIN' $z > /dev/null; then
		sed -i '/$TTL/i $ORIGIN '$(basename ${z%zone}) $z
	fi
done
