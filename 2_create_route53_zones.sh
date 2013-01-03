#!/bin/bash

for z in zones/*.zone; do
	route53 create $(basename ${z%zone})
done
